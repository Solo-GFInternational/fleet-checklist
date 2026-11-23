/*
  Creates the "GF Fleet Trucks" list: one row per truck. scrPreTrip looks the truck up in it to get
  the number of tyres (tyre photos), the truck type (Ambient / Frozen items) and the due dates (shown
  read-only on the checklist with an Expired / Due within 30 days / OK status).

  Columns:
    Title      (display name "Truck number")  e.g. "FJ 101", unique
    TruckType  choice: Ambient / Frozen
    NoOfTyres  number (whole, 1-30)
    ActiveYN   yes/no, default Yes (set No instead of deleting a truck)
    COFExpiry, BlowerServiceDue, TruckServiceDue   date only; the office keeps these current here
  Running it on an existing list adds any missing columns.

  Permissions: the list stops inheriting site permissions, COPYING every existing permission first
  (site Owners/Members keep their access), then Fleet App Drivers get Read and Fleet App Reviewers get
  Fleet App Reviewer (edit items: the office keeps the due dates current). A Read grant that an earlier
  run gave Fleet App Reviewers is removed. Edit the trucks in SharePoint.

  Optional import: paste the contents of files/Fleet Trucks.csv (header row Truck,Type,Tyres) between
  the backticks of CSV_TEXT. Optional extra columns: COF,BlowerService,TruckService (dates as
  yyyy-mm-dd or dd/mm/yyyy). Truck numbers are written the way the app writes them (upper case, a space
  after the 2-letter prefix: "fj101" -> "FJ 101"). Trucks already in the list are skipped.

  Safe to run again: anything that already exists is skipped.

  How to run:
    1. Open the Fleet Operations SharePoint site in Edge or Chrome, signed in as a site Owner.
    2. Press F12, open the Console tab.
    3. Leave DRY_RUN = true for the first run: it only prints what it would do.
    4. Paste this whole file and press Enter. (If the console asks, type "allow pasting" first.)
    5. If the plan looks right, set DRY_RUN = false, paste again and press Enter.
    6. Copy the text it prints (between the ===== lines).
    7. In Power Apps Studio, add "GF Fleet Trucks" as a data source.
*/
(async () => {
  const DRY_RUN = true;
  const LIST = 'GF Fleet Trucks';
  // group -> permission level on the list (Reader = built-in Read)
  const GRANTS = [['Fleet App Drivers', 'Read'], ['Fleet App Reviewers', 'Fleet App Reviewer']];
  const CSV_TEXT = `
`;

  const FIELDS = [
    ['TruckType', '<Field Type="Choice" Name="TruckType" StaticName="TruckType" DisplayName="Truck type" Required="FALSE" ' +
      'Format="Dropdown" FillInChoice="FALSE"><CHOICES><CHOICE>Ambient</CHOICE><CHOICE>Frozen</CHOICE></CHOICES></Field>'],
    ['NoOfTyres', '<Field Type="Number" Name="NoOfTyres" StaticName="NoOfTyres" DisplayName="Number of tyres" Required="FALSE" ' +
      'Decimals="0" Min="1" Max="30" />'],
    ['ActiveYN', '<Field Type="Boolean" Name="ActiveYN" StaticName="ActiveYN" DisplayName="Active" Required="FALSE">' +
      '<Default>1</Default></Field>'],
    ['COFExpiry', '<Field Type="DateTime" Name="COFExpiry" StaticName="COFExpiry" DisplayName="COF expiry" Required="FALSE" Format="DateOnly" />'],
    ['BlowerServiceDue', '<Field Type="DateTime" Name="BlowerServiceDue" StaticName="BlowerServiceDue" DisplayName="Blower service due" Required="FALSE" Format="DateOnly" />'],
    ['TruckServiceDue', '<Field Type="DateTime" Name="TruckServiceDue" StaticName="TruckServiceDue" DisplayName="Truck service due" Required="FALSE" Format="DateOnly" />'],
  ];

  const web = _spPageContextInfo.webAbsoluteUrl;
  const V = 'application/json;odata=verbose';
  const out = [DRY_RUN ? 'DRY RUN (nothing changed)' : 'CHANGING'];
  const digest = (await (await fetch(`${web}/_api/contextinfo`, { method: 'POST', headers: { Accept: V } })).json())
    .d.GetContextWebInformation.FormDigestValue;
  const get = async url => { const r = await fetch(url, { headers: { Accept: V } }); return r.ok ? (await r.json()).d : null; };
  const post = (url, body, extra = {}) => fetch(url, {
    method: 'POST', headers: { Accept: V, 'Content-Type': V, 'X-RequestDigest': digest, ...extra },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const fail = async (what, r) => out.push(`FAILED ${what} (${r.status}) ${(await r.text()).slice(0, 200)}`);
  const q = s => encodeURIComponent(s.replace(/'/g, "''"));
  const listUrl = `${web}/_api/web/lists/getbytitle('${q(LIST)}')`;
  const merge = { 'X-HTTP-Method': 'MERGE', 'IF-MATCH': '*' };
  const truckNo = s => {
    const t = String(s || '').replace(/[\s-]/g, '').toUpperCase();
    return t ? `${t.slice(0, 2)} ${t.slice(2, 12)}` : '';
  };

  // 1. list
  let info = await get(`${listUrl}?$select=Title,HasUniqueRoleAssignments,ListItemEntityTypeFullName`);
  if (info) out.push(`skip list "${LIST}" (exists)`);
  else if (DRY_RUN) out.push(`would create list "${LIST}"`);
  else {
    const r = await post(`${web}/_api/web/lists`, {
      __metadata: { type: 'SP.List' }, BaseTemplate: 100, Title: LIST,
      Description: 'Fleet Checklist app: one row per truck (type and number of tyres). Edit here; the app reads it.',
    });
    if (!r.ok) { await fail(`create list "${LIST}"`, r); console.log('=====\n' + out.join('\n') + '\n====='); return; }
    out.push(`created list "${LIST}"`);
    info = await get(`${listUrl}?$select=Title,HasUniqueRoleAssignments,ListItemEntityTypeFullName`);
  }

  // 2. columns
  const have = info ? new Map(((await get(`${listUrl}/fields?$select=InternalName,Title,Indexed,EnforceUniqueValues`))?.results || [])
    .map(f => [f.InternalName, f])) : new Map();
  const title = have.get('Title');
  if (title && title.Title === 'Truck number' && title.Indexed && title.EnforceUniqueValues) out.push('skip Title column (already "Truck number", unique)');
  else if (DRY_RUN) out.push('would set Title column: display name "Truck number", indexed, unique values');
  else {
    const r = await post(`${listUrl}/fields/getbyinternalnameortitle('Title')`,
      { __metadata: { type: 'SP.Field' }, Title: 'Truck number', Indexed: true, EnforceUniqueValues: true }, merge);
    if (r.ok) out.push('Title column: "Truck number", indexed, unique values'); else await fail('Title column', r);
  }
  for (const [name, xml] of FIELDS) {
    if (have.has(name)) { out.push(`skip column ${name} (exists as "${have.get(name).Title}")`); continue; }
    if (DRY_RUN) { out.push(`would create column ${name}`); continue; }
    const r = await post(`${listUrl}/fields/createfieldasxml`, {
      parameters: { __metadata: { type: 'SP.XmlSchemaFieldCreationInformation' }, SchemaXml: xml, Options: 1 | 8 | 16 },
    });
    if (!r.ok) { await fail(`column ${name}`, r); continue; }
    const f = (await r.json()).d;
    out.push(f.InternalName === name ? `created column ${name} "${f.Title}"` : `CHECK column ${f.InternalName} (expected ${name})`);
  }

  // 3. permissions: stop inheriting (copy existing); Drivers Read, Reviewers Fleet App Reviewer (edit)
  const roleId = async name => name === 'Read'
    ? (await get(`${web}/_api/web/roledefinitions/getbytype(2)?$select=Id`))?.Id // 2 = Reader
    : (await get(`${web}/_api/web/roledefinitions/getbyname('${q(name)}')?$select=Id`))?.Id;
  const readId = await roleId('Read');
  if (DRY_RUN) {
    out.push(`${LIST}: ${info && info.HasUniqueRoleAssignments ? 'already has its own permissions' : 'would stop inheriting (copying all existing permissions)'}; ` +
      `would grant ${GRANTS.map(([g, l]) => `${g} -> ${l}`).join(', ')}`);
  } else if (info) {
    if (!info.HasUniqueRoleAssignments) {
      const r = await post(`${listUrl}/breakroleinheritance(copyRoleAssignments=true,clearSubscopes=false)`);
      if (r.ok) out.push(`${LIST}: stopped inheriting (existing permissions copied)`); else await fail(`${LIST}: stop inheriting`, r);
    }
    for (const [g, level] of GRANTS) {
      const grp = await get(`${web}/_api/web/sitegroups/getbyname('${q(g)}')?$select=Id`);
      const id = await roleId(level);
      if (!grp || !id) { out.push(`FAILED ${LIST}: group "${g}" or level "${level}" not found (run setup_app_permissions.js first)`); continue; }
      const r = await post(`${listUrl}/roleassignments/addroleassignment(principalid=${grp.Id},roledefid=${id})`);
      out.push(r.ok ? `${LIST}: ${g} -> ${level}` : `FAILED ${LIST}: ${g} (${r.status})`);
      if (r.ok && id !== readId) { // an earlier run gave this group Read: take it away
        const rr = await post(`${listUrl}/roleassignments/removeroleassignment(principalid=${grp.Id},roledefid=${readId})`);
        if (rr.ok) out.push(`${LIST}: ${g} Read removed (if it was there)`);
      }
    }
  }

  // 4. optional CSV import
  const lines = CSV_TEXT.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
  if (lines.length) {
    const head = lines[0].split(',').map(h => h.trim().toLowerCase());
    const iTruck = head.indexOf('truck'), iType = head.indexOf('type'), iTyres = head.indexOf('tyres');
    const DATE_COLS = [['cof', 'COFExpiry'], ['blowerservice', 'BlowerServiceDue'], ['truckservice', 'TruckServiceDue']]
      .map(([h, col]) => [head.indexOf(h), col]).filter(([i]) => i >= 0);
    const isoDate = v => { // yyyy-mm-dd or dd/mm/yyyy -> yyyy-mm-dd (null if not a date)
      let m = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(v || '');
      if (m) return `${m[1]}-${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}`;
      m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(v || '');
      return m ? `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}` : null;
    };
    // date-only columns: write noon in the site's time zone, so the date shows the same everywhere
    const bias = (await get(`${web}/_api/web/RegionalSettings/TimeZone/Information`))?.Bias || 0; // minutes, UTC = local + bias
    const noonUtc = d => new Date(Date.parse(`${d}T12:00:00Z`) + bias * 60000).toISOString();
    if (iTruck < 0) out.push('FAILED CSV: header must have a "Truck" column (Truck,Type,Tyres)');
    else {
      const existingTitles = new Set(info ? ((await get(`${listUrl}/items?$select=Title&$top=5000`))?.results || [])
        .map(i => truckNo(i.Title)) : []);
      let added = 0, skipped = 0;
      for (const line of lines.slice(1)) {
        const c = line.split(',').map(x => x.trim());
        const t = truckNo(c[iTruck]);
        if (!t) continue;
        if (existingTitles.has(t)) { skipped++; continue; }
        const typeRaw = iType >= 0 ? (c[iType] || '').toLowerCase() : '';
        const type = typeRaw.startsWith('f') ? 'Frozen' : typeRaw.startsWith('a') ? 'Ambient' : null;
        const tyres = iTyres >= 0 && c[iTyres] ? parseInt(c[iTyres], 10) : null;
        const dates = DATE_COLS.map(([i, col]) => [col, isoDate(c[i])]).filter(([, d]) => d);
        existingTitles.add(t);
        if (DRY_RUN) { out.push(`would add truck ${t}  ${type || '(no type)'}  ${tyres || '(no tyre count)'}  ${dates.map(d => d.join(' ')).join('  ')}`); added++; continue; }
        const body = { __metadata: { type: info.ListItemEntityTypeFullName }, Title: t, ActiveYN: true };
        if (type) body.TruckType = type;
        if (Number.isFinite(tyres)) body.NoOfTyres = tyres;
        for (const [col, d] of dates) body[col] = noonUtc(d);
        const r = await post(`${listUrl}/items`, body);
        if (r.ok) added++; else await fail(`add truck ${t}`, r);
      }
      out.push(`CSV: ${DRY_RUN ? 'would add' : 'added'} ${added}, skipped ${skipped} already in the list`);
    }
  } else out.push('CSV: nothing pasted into CSV_TEXT, no trucks imported');

  console.log('=====\n' + out.join('\n') + '\n=====');
})();
