/*
  Creates the "GF Fleet Daily Reviews" list: one star score (1-5) per driver per day, given by a reviewer
  on the Review and sign-off screen (Daily review tab). The driver sees their latest score on the home screen.

  Safe to run again: an existing list, column, index or permission is skipped, never changed.

  What it does:
    1. Creates the list (Title is relabelled "Driver") with columns:
         DriverEmail (text, lower case), ReviewDate (date only), Stars (number 1-5),
         Comment (multi-line plain text), ReviewerName (text), ActiveYN (Yes/No, default Yes)
    2. Indexes DriverEmail and ReviewDate (the app filters on both).
    3. Stops inheriting site permissions, COPYING every existing permission first, then grants
         Fleet App Reviewers -> Fleet App Reviewer (view, add, edit; no delete)
         Fleet App Drivers   -> Read
       The groups and the Fleet App Reviewer level come from setup_app_permissions.js: run that first.
       Note: the app only shows a driver their own scores, but a driver opening the list in SharePoint
       can see everyone's. Per-driver privacy would need a flow setting item permissions (later).

  How to run:
    1. Open the Fleet Operations SharePoint site in Edge or Chrome, signed in as a site Owner.
    2. Press F12, open the Console tab.
    3. Leave DRY_RUN = true for the first run: it only prints what it would do.
    4. Paste this whole file and press Enter. (If the console asks, type "allow pasting" first.)
    5. If the plan looks right, set DRY_RUN = false, paste again and press Enter.
    6. Copy the text it prints (between the ===== lines).
    7. In Power Apps Studio: Data -> Add data -> SharePoint -> the site -> "GF Fleet Daily Reviews".
*/
(async () => {
  const DRY_RUN = true;
  const LIST = 'GF Fleet Daily Reviews';
  const GROUP_DRIVERS = 'Fleet App Drivers';
  const GROUP_REVIEWERS = 'Fleet App Reviewers';
  const REVIEWER_LEVEL = 'Fleet App Reviewer';

  // Title (built in) holds the driver's name.
  const FIELDS = [
    ['DriverEmail', '<Field Type="Text" Name="DriverEmail" StaticName="DriverEmail" DisplayName="Driver email" Required="TRUE" MaxLength="255" />'],
    ['ReviewDate', '<Field Type="DateTime" Name="ReviewDate" StaticName="ReviewDate" DisplayName="Review date" Required="TRUE" Format="DateOnly" />'],
    ['Stars', '<Field Type="Number" Name="Stars" StaticName="Stars" DisplayName="Stars" Required="TRUE" Min="1" Max="5" Decimals="0" />'],
    ['Comment', '<Field Type="Note" Name="Comment" StaticName="Comment" DisplayName="Comment" NumLines="6" RichText="FALSE" />'],
    ['ReviewerName', '<Field Type="Text" Name="ReviewerName" StaticName="ReviewerName" DisplayName="Reviewer" MaxLength="255" />'],
    ['ActiveYN', '<Field Type="Boolean" Name="ActiveYN" StaticName="ActiveYN" DisplayName="Active"><Default>1</Default></Field>'],
  ];
  const INDEXED = ['DriverEmail', 'ReviewDate'];

  const web = _spPageContextInfo.webAbsoluteUrl;
  const V = 'application/json;odata=verbose';
  const q = s => encodeURIComponent(s.replace(/'/g, "''"));
  const listUrl = `${web}/_api/web/lists/getbytitle('${q(LIST)}')`;
  const out = [DRY_RUN ? 'DRY RUN (nothing changed)' : 'CREATING'];
  const digest = (await (await fetch(`${web}/_api/contextinfo`, { method: 'POST', headers: { Accept: V } })).json())
    .d.GetContextWebInformation.FormDigestValue;
  const get = async url => { const r = await fetch(url, { headers: { Accept: V } }); return r.ok ? (await r.json()).d : null; };
  const post = (url, body, extra = {}) => fetch(url, {
    method: 'POST', headers: { Accept: V, 'Content-Type': V, 'X-RequestDigest': digest, ...extra },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const merge = (url, body) => post(url, body, { 'X-HTTP-Method': 'MERGE', 'IF-MATCH': '*' });
  const fail = async (what, r) => out.push(`FAILED ${what} (${r.status}) ${(await r.text()).slice(0, 200)}`);

  // 1. list
  let info = await get(`${listUrl}?$select=Title,HasUniqueRoleAssignments`);
  if (!info) {
    if (DRY_RUN) {
      out.push(`would create list "${LIST}" with columns ${FIELDS.map(f => f[0]).join(', ')}`,
        `would index ${INDEXED.join(', ')}`,
        `would stop inheriting (copying all existing permissions); would grant ${GROUP_REVIEWERS} -> ${REVIEWER_LEVEL}, ${GROUP_DRIVERS} -> Read`);
      console.log('=====\n' + out.join('\n') + '\n====='); return;
    }
    const r = await post(`${web}/_api/web/lists`, {
      __metadata: { type: 'SP.List' }, BaseTemplate: 100, Title: LIST,
      Description: 'Fleet Checklist app: one star score per driver per day. Deactivate rows instead of deleting them.',
    });
    if (!r.ok) { await fail(`create list "${LIST}"`, r); console.log('=====\n' + out.join('\n') + '\n====='); return; }
    out.push(`created list "${LIST}"`);
    info = await get(`${listUrl}?$select=Title,HasUniqueRoleAssignments`);
  } else out.push(`list "${LIST}" already exists`);

  // 2. columns
  const fields = (await get(`${listUrl}/fields?$select=InternalName,Indexed,Title`)).results;
  const have = new Map(fields.map(f => [f.InternalName, f]));
  for (const [name, xml] of FIELDS) {
    if (have.has(name)) { out.push(`skip column ${name} (exists)`); continue; }
    if (DRY_RUN) { out.push(`would create column ${name}`); continue; }
    const r = await post(`${listUrl}/fields/createfieldasxml`, {
      parameters: { __metadata: { type: 'SP.XmlSchemaFieldCreationInformation' }, SchemaXml: xml, Options: 1 | 8 | 16 },
    });
    if (r.ok) out.push(`created column ${name}`); else await fail(`column ${name}`, r);
  }
  if (have.get('Title')?.Title !== 'Driver') {
    if (DRY_RUN) out.push('would relabel Title as "Driver"');
    else {
      const r = await merge(`${listUrl}/fields/getbyinternalnameortitle('Title')`, { __metadata: { type: 'SP.Field' }, Title: 'Driver' });
      if (r.ok) out.push('relabelled Title as "Driver"'); else await fail('relabel Title', r);
    }
  }

  // 3. indexes
  for (const name of INDEXED) {
    if (have.get(name)?.Indexed) { out.push(`skip index ${name} (exists)`); continue; }
    if (DRY_RUN) { out.push(`would index ${name}`); continue; }
    const r = await merge(`${listUrl}/fields/getbyinternalnameortitle('${name}')`, { __metadata: { type: 'SP.Field' }, Indexed: true });
    if (r.ok) out.push(`indexed ${name}`); else await fail(`index ${name}`, r);
  }

  // 4. permissions
  const groupId = {};
  for (const g of [GROUP_DRIVERS, GROUP_REVIEWERS]) groupId[g] = (await get(`${web}/_api/web/sitegroups/getbyname('${q(g)}')?$select=Id`))?.Id;
  const reviewerLevelId = (await get(`${web}/_api/web/roledefinitions/getbyname('${q(REVIEWER_LEVEL)}')?$select=Id`))?.Id;
  const readId = (await get(`${web}/_api/web/roledefinitions/getbytype(2)?$select=Id`))?.Id; // 2 = Reader
  const grants = [[GROUP_REVIEWERS, reviewerLevelId, REVIEWER_LEVEL], [GROUP_DRIVERS, readId, 'Read']];
  if (!info.HasUniqueRoleAssignments) {
    if (DRY_RUN) out.push('would stop inheriting (copying all existing permissions)');
    else {
      const r = await post(`${listUrl}/breakroleinheritance(copyRoleAssignments=true,clearSubscopes=false)`);
      if (r.ok) out.push('stopped inheriting (existing permissions copied)'); else await fail('stop inheriting', r);
    }
  } else out.push('list already has its own permissions');
  for (const [group, roleId, levelName] of grants) {
    if (!groupId[group] || !roleId) {
      out.push(`SKIPPED ${group} -> ${levelName}: group or permission level missing. Run setup_app_permissions.js first, then this again.`);
      continue;
    }
    if (DRY_RUN) { out.push(`would grant ${group} -> ${levelName}`); continue; }
    const r = await post(`${listUrl}/roleassignments/addroleassignment(principalid=${groupId[group]},roledefid=${roleId})`);
    if (r.ok) out.push(`${group} -> ${levelName}`); else await fail(`${group} -> ${levelName}`, r);
  }

  console.log('=====\n' + out.join('\n') + '\n=====');
})();
