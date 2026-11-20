/*
  Creates the 19 "Accessory Checks" columns on the Fleet Checklist list
  (see files/Fleet Checklist - Accessory Checks columns.md).

  Each column is created with the exact internal name the app uses AND its display
  name in one step, so there is no "type internal name, then rename" step.
  Columns that already exist (same internal name) are skipped, so it is safe to run again.

  How to run:
    1. Open the Fleet Operations SharePoint site in Edge or Chrome (any page of the site),
       signed in as someone who can edit the list's columns (site Member or Owner).
    2. Press F12, open the Console tab.
    3. Leave DRY_RUN = true for the first run: it only prints what it would do.
    4. Paste this whole file and press Enter. (If the console asks, type "allow pasting" first.)
    5. If the plan looks right, set DRY_RUN = false, paste again and press Enter.
    6. Copy the text it prints (between the ===== lines).
*/
(async () => {
  const LIST = 'Fleet Checklist';
  const DRY_RUN = true;

  // [internal name, display name, kind]   kind: date | yesno | note
  const COLUMNS = [
    ['AccCOFExpiry', 'COF Expiry Date', 'date'],
    ['AccBlowerServiceDue', 'Blower Service Due Date', 'date'],
    ['AccTruckServiceDue', 'Truck Service Due Date', 'date'],
    ['AccSpareTyre', 'Spare Tyre Availability', 'yesno'],
    ['AccTyreCondition', 'Tyre Condition', 'yesno'],
    ['AccCabinClean', 'Cabin Cleanliness', 'yesno'],
    ['AccFireExtinguisher', 'Fire Extinguisher Mounted and Serviceable', 'yesno'],
    ['AccFirstAidKit', 'First Aid Kit Available', 'yesno'],
    ['AccTrafficCones', 'Traffic Cones Available', 'yesno'],
    ['AccFuelCard', 'Fuel Card Available', 'yesno'],
    ['AccPlugWire', 'Plug Wire Available', 'yesno'],
    ['AccMats', 'Mats Available', 'yesno'],
    ['AccEngJack', 'Engraved Jack Available', 'yesno'],
    ['AccEngWheelBrace', 'Engraved Wheel Brace Available', 'yesno'],
    ['AccEngPipe', 'Engraved Pipe Available', 'yesno'],
    ['AccEngTyreWinder', 'Engraved Spare Tyre Winder Available', 'yesno'],
    ['AccEngTrolley', 'Engraved Trolley Available', 'yesno'],
    ['AccTruckFloor', 'Truck Floor Condition', 'yesno'],
    ['AccComments', 'Accessory Checks – comments', 'note'],
  ];

  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const schema = (name, title, kind) => {
    const common = `Name="${name}" StaticName="${name}" DisplayName="${esc(title)}" Required="FALSE"`;
    if (kind === 'date') return `<Field Type="DateTime" ${common} Format="DateOnly" FriendlyDisplayFormat="Disabled" />`;
    if (kind === 'note') return `<Field Type="Note" ${common} NumLines="6" RichText="FALSE" AppendOnly="FALSE" />`;
    // Yes/No choice: no default, single select, no fill-in values
    return `<Field Type="Choice" ${common} Format="Dropdown" FillInChoice="FALSE">` +
      '<CHOICES><CHOICE>Yes</CHOICE><CHOICE>No</CHOICE></CHOICES></Field>';
  };

  const web = _spPageContextInfo.webAbsoluteUrl;
  const list = `${web}/_api/web/lists/getbytitle('${encodeURIComponent(LIST.replace(/'/g, "''"))}')`;
  const JSON_V = 'application/json;odata=verbose';
  const out = [];

  const existingRes = await fetch(`${list}/fields?$select=InternalName,Title`, { headers: { Accept: JSON_V } });
  if (!existingRes.ok) { console.log(`List "${LIST}" not found or no access (${existingRes.status})`); return; }
  const existing = new Map((await existingRes.json()).d.results.map(f => [f.InternalName, f.Title]));

  const digestRes = await fetch(`${web}/_api/contextinfo`, { method: 'POST', headers: { Accept: JSON_V } });
  const digest = (await digestRes.json()).d.GetContextWebInformation.FormDigestValue;

  out.push(`${DRY_RUN ? 'DRY RUN (nothing changed)' : 'CREATING'} on list "${LIST}"`);
  let created = 0, skipped = 0, failed = 0;
  for (const [name, title, kind] of COLUMNS) {
    if (existing.has(name)) { out.push(`skip    ${name}  (already exists as "${existing.get(name)}")`); skipped++; continue; }
    if (DRY_RUN) { out.push(`would create  ${name}  "${title}"  ${kind}`); continue; }
    const r = await fetch(`${list}/fields/createfieldasxml`, {
      method: 'POST',
      headers: { Accept: JSON_V, 'Content-Type': JSON_V, 'X-RequestDigest': digest },
      body: JSON.stringify({
        parameters: {
          __metadata: { type: 'SP.XmlSchemaFieldCreationInformation' },
          SchemaXml: schema(name, title, kind),
          Options: 1 | 8 | 16, // default content type + keep internal name + add to default view
        },
      }),
    });
    if (!r.ok) { out.push(`FAILED  ${name}  (${r.status}) ${(await r.text()).slice(0, 200)}`); failed++; continue; }
    const f = (await r.json()).d;
    const ok = f.InternalName === name;
    out.push(`${ok ? 'created' : 'CHECK  '} ${f.InternalName}  "${f.Title}"  ${f.TypeAsString}` +
      (ok ? '' : `   <-- expected internal name ${name}`));
    if (ok) created++; else failed++;
  }
  out.push('', `created ${created}, skipped ${skipped}, problems ${failed}`);
  console.log('=====\n' + out.join('\n') + '\n=====');
})();
