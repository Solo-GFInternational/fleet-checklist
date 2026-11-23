/*
  Run sheet v2: creates the columns the new run sheet screen needs, with an exact internal name AND
  display name in one step. Columns that already exist (same internal name) are skipped, so it is
  safe to run again.

    Run Sheet Details / NoofInvoices   number of invoices at the stop (one invoice photo each)
    Fleet Photos      / RunKey         the run's LocalKey, so photos can upload before the run row exists
    Fleet Photos      / StopKey        the stop's LocalKey, so each photo is linked to its stop

  After running it, add RunKey and StopKey as optional text inputs to the SaveFleetPhoto flow
  (see PROJECT_HANDOVER.md), then remove and re-add the flow in the app.

  How to run:
    1. Open the Fleet Operations SharePoint site in Edge or Chrome (any page of the site),
       signed in as someone who can edit the lists' columns (site Member or Owner).
    2. Press F12, open the Console tab.
    3. Leave DRY_RUN = true for the first run: it only prints what it would do.
    4. Paste this whole file and press Enter. (If the console asks, type "allow pasting" first.)
    5. If the plan looks right, set DRY_RUN = false, paste again and press Enter.
    6. Copy the text it prints (between the ===== lines).
*/
(async () => {
  const DRY_RUN = true;

  // [list or library, internal name, display name, kind]   kind: number | text
  // Lines starting with // are skipped. Columns that already exist are always skipped.
  const COLUMNS = [
    ['Run Sheet Details', 'NoofInvoices', 'No of invoices', 'number'],
    ['Fleet Photos', 'RunKey', 'Run key', 'text'],
    ['Fleet Photos', 'StopKey', 'Stop key', 'text'],
  ];

  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const schema = (name, title, kind) => {
    const common = `Name="${name}" StaticName="${name}" DisplayName="${esc(title)}" Required="FALSE"`;
    if (kind === 'number') return `<Field Type="Number" ${common} Decimals="0" Min="0" />`;
    if (kind === 'text') return `<Field Type="Text" ${common} MaxLength="255" />`;
    throw new Error(`unknown kind ${kind} for ${name}`);
  };

  const web = _spPageContextInfo.webAbsoluteUrl;
  const JSON_V = 'application/json;odata=verbose';
  const listUrl = t => `${web}/_api/web/lists/getbytitle('${encodeURIComponent(t.replace(/'/g, "''"))}')`;
  const digestRes = await fetch(`${web}/_api/contextinfo`, { method: 'POST', headers: { Accept: JSON_V } });
  const digest = (await digestRes.json()).d.GetContextWebInformation.FormDigestValue;

  const out = [DRY_RUN ? 'DRY RUN (nothing changed)' : 'CREATING'];
  const existingByList = {};
  let created = 0, skipped = 0, failed = 0;
  for (const [list, name, title, kind] of COLUMNS) {
    if (!existingByList[list]) {
      const r = await fetch(`${listUrl(list)}/fields?$select=InternalName,Title`, { headers: { Accept: JSON_V } });
      if (!r.ok) { out.push(`FAILED  list "${list}" not found or no access (${r.status})`); failed++; continue; }
      existingByList[list] = new Map((await r.json()).d.results.map(f => [f.InternalName, f.Title]));
    }
    const existing = existingByList[list];
    if (existing.has(name)) { out.push(`skip    ${list} / ${name}  (already exists as "${existing.get(name)}")`); skipped++; continue; }
    if (DRY_RUN) { out.push(`would create  ${list} / ${name}  "${title}"  ${kind}`); continue; }
    const r = await fetch(`${listUrl(list)}/fields/createfieldasxml`, {
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
    if (!r.ok) { out.push(`FAILED  ${list} / ${name}  (${r.status}) ${(await r.text()).slice(0, 200)}`); failed++; continue; }
    const f = (await r.json()).d;
    const ok = f.InternalName === name;
    out.push(`${ok ? 'created' : 'CHECK  '} ${list} / ${f.InternalName}  "${f.Title}"  ${f.TypeAsString}` +
      (ok ? '' : `   <-- expected internal name ${name}`));
    if (ok) created++; else failed++;
  }
  out.push('', `created ${created}, skipped ${skipped}, problems ${failed}`);
  console.log('=====\n' + out.join('\n') + '\n=====');
})();
