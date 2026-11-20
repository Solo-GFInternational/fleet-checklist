/*
  Creates a TEST Fleet Checklist row, filled in like a real driver submission, plus test photos
  (odometer + the 18 accessory items) in the photo library, linked to that row.
  Use it to trigger and test the Power Automate flows without going through the app.

  Every value is clearly marked as a test (remarks "AUTOMATED TEST RECORD"; the truck is one of the 9 test registrations),
  so test rows are easy to find and delete afterwards.

  How to run:
    1. Open the Fleet Operations SharePoint site in Edge or Chrome (any page of the site).
    2. Set the SETTINGS below (at least PHOTO_LIBRARY: the library the SaveFleetPhoto flow saves to).
    3. Press F12 → Console, paste this whole file, press Enter. (Type "allow pasting" first if asked.)
    4. Leave DRY_RUN = true the first time: it only prints what it would create.
    5. Set DRY_RUN = false and run again. Copy the text between the ===== lines if anything fails.

  SIGN_OFF = true also fills in the manager's sign-off (Approval For Delivery etc.) on the same row,
  which is what triggers the "Fleet Checklist – email to MEX" flow.
*/
(async () => {
  // ------------------------------------------------------------------ SETTINGS
  const DRY_RUN = true;
  const SIGN_OFF = false;                 // true = also act as the manager signing it off
  const LIST = 'Fleet Checklist';
  const PHOTO_LIBRARY = 'Fleet Photos';   // the document library SaveFleetPhoto writes to
  const PHOTO_FOLDER = '';                // sub-folder inside it, e.g. 'Checklist photos' ('' = top level)
  // Test registrations from files/Fiji Number Plate QR Codes samples.docx; one is picked at random each run.
  const TRUCKS = ['FJ 101', 'CA 203', 'KI 123', 'LA 456', 'HX 789', 'GV 312', 'EF 645', 'JK 908', 'BN 274'];
  const TRUCK = TRUCKS[Math.floor(Math.random() * TRUCKS.length)];
  const NO_ANSWERS = 2;                   // how many Yes/No questions to answer "No"
  // Photo library columns the flow fills in (internal names). Ones that don't exist are skipped.
  const PHOTO_COLUMNS = { truck: 'Truck', type: 'PhotoType', item: 'Item', recordId: 'RecordID', source: 'SourceList' };
  // ------------------------------------------------------------------

  const web = _spPageContextInfo.webAbsoluteUrl;
  const me = _spPageContextInfo.userDisplayName || 'Test Driver';
  const J = 'application/json;odata=verbose';
  const out = [DRY_RUN ? 'DRY RUN (nothing created)' : 'CREATING TEST DATA'];
  const get = async url => { const r = await fetch(url, { headers: { Accept: J } }); if (!r.ok) throw new Error(`${r.status} ${url}`); return (await r.json()).d; };
  const digest = (await (await fetch(`${web}/_api/contextinfo`, { method: 'POST', headers: { Accept: J } })).json())
    .d.GetContextWebInformation.FormDigestValue;
  const list = t => `${web}/_api/web/lists/getbytitle('${encodeURIComponent(t.replace(/'/g, "''"))}')`;
  const today = new Date();
  const iso = d => d.toISOString();
  const addDays = n => { const d = new Date(today); d.setDate(d.getDate() + n); return d; };

  try {
    // ---- 1. Build the checklist row from the list's own columns
    const listInfo = await get(`${list(LIST)}?$select=ListItemEntityTypeFullName`);
    const fields = (await get(`${list(LIST)}/fields?$filter=Hidden eq false and ReadOnlyField eq false&$select=InternalName,Title,TypeAsString,Choices`)).results;
    const byName = Object.fromEntries(fields.map(f => [f.InternalName, f]));
    const SIGNOFF = ['field_52', 'field_53', 'field_54', 'field_55'];
    const yesNo = fields.filter(f => f.TypeAsString === 'Choice' && !SIGNOFF.includes(f.InternalName)
      && (f.Choices.results || []).includes('Yes'));
    const noSet = new Set(yesNo.sort(() => Math.random() - 0.5).slice(0, NO_ANSWERS).map(f => f.InternalName));

    const row = { __metadata: { type: listInfo.ListItemEntityTypeFullName } };
    if (byName.Title) row.Title = `TEST ${today.toISOString().slice(0, 16)}`;
    for (const f of fields) {
      const n = f.InternalName;
      if (SIGNOFF.includes(n) || n === 'Title' || n === 'MEXSent') continue;
      if (!/^(field_\d+|Acc\w+|NextServiceDue)$/.test(n)) continue;
      if (n === 'field_1') row[n] = TRUCK;
      else if (n === 'field_2') row[n] = me;
      else if (n === 'field_3') row[n] = 'Test site';
      else if (n === 'field_50') row[n] = 123456;
      else if (n === 'NextServiceDue') row[n] = 130000;
      else if (n === 'field_51') row[n] = 'AUTOMATED TEST RECORD – safe to delete.';
      else if (f.TypeAsString === 'Choice' && (f.Choices.results || []).includes('Yes')) row[n] = noSet.has(n) ? 'No' : 'Yes';
      else if (f.TypeAsString === 'DateTime') row[n] = iso(n === 'AccCOFExpiry' ? addDays(180) : addDays(60));
      else if (f.TypeAsString === 'Note' || f.TypeAsString === 'Text') row[n] = `Test comment (${f.Title})`;
      else if (f.TypeAsString === 'Number') row[n] = 1;
    }
    out.push(`Checklist row: ${Object.keys(row).length - 1} fields, "No" on: ${[...noSet].map(n => byName[n].Title).join('; ') || 'none'}`);

    let itemId = '(dry run)';
    if (!DRY_RUN) {
      const r = await fetch(`${list(LIST)}/items`, { method: 'POST', headers: { Accept: J, 'Content-Type': J, 'X-RequestDigest': digest }, body: JSON.stringify(row) });
      if (!r.ok) throw new Error(`Creating the checklist failed (${r.status}): ${(await r.text()).slice(0, 300)}`);
      itemId = (await r.json()).d.Id;
      out.push(`created checklist ID ${itemId}`);
    }

    // ---- 2. Photos: odometer + one per accessory item, drawn in the browser
    const accTitles = fields.filter(f => /^Acc/.test(f.InternalName) && f.InternalName !== 'AccComments').map(f => f.Title);
    const photos = [{ type: 'Odometer', item: 'Odometer' }, ...accTitles.map(t => ({ type: 'Accessory', item: t }))];
    const draw = text => new Promise(res => {
      const c = document.createElement('canvas'); c.width = 640; c.height = 480;
      const g = c.getContext('2d');
      g.fillStyle = '#089090'; g.fillRect(0, 0, 640, 480);
      g.fillStyle = '#f8d000'; g.fillRect(0, 440, 640, 40);
      g.fillStyle = '#ffffff'; g.font = 'bold 34px Segoe UI, Arial'; g.textAlign = 'center';
      g.fillText('TEST PHOTO', 320, 170);
      g.font = '26px Segoe UI, Arial';
      const words = text.split(' '); let line = '', y = 240;
      for (const w of words) { if (g.measureText(line + w).width > 560) { g.fillText(line, 320, y); line = ''; y += 34; } line += w + ' '; }
      g.fillText(line, 320, y);
      g.font = '20px Segoe UI, Arial'; g.fillText(`${TRUCK} · ${today.toLocaleString()}`, 320, 410);
      c.toBlob(res, 'image/jpeg', 0.85);
    });

    const libInfo = await get(`${list(PHOTO_LIBRARY)}?$select=ListItemEntityTypeFullName&$expand=RootFolder`);
    const folderUrl = libInfo.RootFolder.ServerRelativeUrl + (PHOTO_FOLDER ? '/' + PHOTO_FOLDER : '');
    const libFields = new Set((await get(`${list(PHOTO_LIBRARY)}/fields?$select=InternalName`)).results.map(f => f.InternalName));
    const meta = Object.fromEntries(Object.entries(PHOTO_COLUMNS).filter(([, col]) => libFields.has(col)));
    const missing = Object.values(PHOTO_COLUMNS).filter(col => !libFields.has(col));
    if (missing.length) out.push(`note: photo library has no column(s) ${missing.join(', ')} – skipped`);
    out.push(`${photos.length} photos → ${PHOTO_LIBRARY}${PHOTO_FOLDER ? '/' + PHOTO_FOLDER : ''}`);

    let ok = 0;
    for (const p of photos) {
      const safe = p.item.replace(/[\\/:*?"<>|#%]/g, '-');
      const name = `${TRUCK.replace(/\s/g, '')}_${itemId}_${p.type}_${safe}_${Date.now()}.jpg`;
      if (DRY_RUN) { out.push(`  would upload ${name}`); continue; }
      const blob = await draw(p.item);
      const up = await fetch(`${web}/_api/web/GetFolderByServerRelativeUrl('${encodeURIComponent(folderUrl)}')/Files/add(url='${encodeURIComponent(name)}',overwrite=true)?$expand=ListItemAllFields`,
        { method: 'POST', headers: { Accept: J, 'X-RequestDigest': digest }, body: blob });
      if (!up.ok) { out.push(`  FAILED ${p.item} (${up.status}) ${(await up.text()).slice(0, 200)}`); continue; }
      const fileItemId = (await up.json()).d.ListItemAllFields.Id;
      const values = { __metadata: { type: libInfo.ListItemEntityTypeFullName } };
      if (meta.truck) values[meta.truck] = TRUCK;
      if (meta.type) values[meta.type] = p.type;
      if (meta.item) values[meta.item] = p.item;
      if (meta.recordId) values[meta.recordId] = itemId;
      if (meta.source) values[meta.source] = LIST;
      const m = await fetch(`${list(PHOTO_LIBRARY)}/items(${fileItemId})`, {
        method: 'POST', headers: { Accept: J, 'Content-Type': J, 'X-RequestDigest': digest, 'X-HTTP-Method': 'MERGE', 'IF-MATCH': '*' }, body: JSON.stringify(values) });
      if (!m.ok) out.push(`  uploaded ${p.item}, but columns not set (${m.status})`); else ok++;
    }
    if (!DRY_RUN) out.push(`uploaded ${ok} of ${photos.length} photos with their details`);

    // ---- 3. Optional manager sign-off (triggers the MEX email flow)
    if (SIGN_OFF) {
      const first = n => (byName[n] && byName[n].Choices.results || [])[0];
      const signoff = { __metadata: { type: listInfo.ListItemEntityTypeFullName } };
      if (byName.field_52) signoff.field_52 = first('field_52');
      if (byName.field_53) signoff.field_53 = first('field_53');
      if (byName.field_54) signoff.field_54 = me;
      if (byName.field_55) signoff.field_55 = iso(today);
      out.push(`sign-off: Approval "${signoff.field_52}", Send For Repairs "${signoff.field_53}"`);
      if (!DRY_RUN) {
        const r = await fetch(`${list(LIST)}/items(${itemId})`, { method: 'POST',
          headers: { Accept: J, 'Content-Type': J, 'X-RequestDigest': digest, 'X-HTTP-Method': 'MERGE', 'IF-MATCH': '*' }, body: JSON.stringify(signoff) });
        out.push(r.ok ? 'signed off (the MEX flow should run within a minute)' : `sign-off FAILED (${r.status}) ${(await r.text()).slice(0, 200)}`);
      }
    }
  } catch (e) {
    out.push('STOPPED: ' + e.message);
  }
  console.log('=====\n' + out.join('\n') + '\n=====');
})();
