/*
  Prints the columns of SharePoint lists (display name, internal name, type,
  required, choices, lookup target) so screen code can use the exact internal names.

  How to run:
    1. Open the Fleet Operations SharePoint site in Edge or Chrome (any page of the site).
    2. Press F12, open the Console tab.
    3. Change LISTS below if needed, paste this whole file and press Enter.
       (If the console asks, type "allow pasting" first.)
    4. Copy the text it prints (between the ===== lines).
*/
(async () => {
  const LISTS = ['Driver Declarations'];
  const web = _spPageContextInfo.webAbsoluteUrl;
  const out = [];
  for (const title of LISTS) {
    const url = web + `/_api/web/lists/getbytitle('${encodeURIComponent(title)}')/fields` +
      '?$filter=Hidden eq false and ReadOnlyField eq false' +
      '&$select=Title,InternalName,TypeAsString,Required,Choices,LookupList,LookupField';
    const r = await fetch(url, { headers: { Accept: 'application/json;odata=nometadata' } });
    if (!r.ok) { out.push(`## ${title}: NOT FOUND (${r.status})`); continue; }
    const fields = (await r.json()).value
      .filter(f => !['ContentType', 'Attachments', '_ColorTag', 'ComplianceAssetId'].includes(f.InternalName));
    out.push(`## ${title}`);
    out.push('Display name | Internal name | Type | Required | Choices / lookup');
    for (const f of fields) {
      const extra = f.Choices && f.Choices.length ? f.Choices.join(', ')
        : f.LookupField ? `lookup -> ${f.LookupField}` : '';
      out.push(`${f.Title} | ${f.InternalName} | ${f.TypeAsString} | ${f.Required ? 'yes' : ''} | ${extra}`);
    }
    out.push('');
  }
  console.log('=====\n' + out.join('\n') + '\n=====');
})();
