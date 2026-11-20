/*
  Creates the "GF Fleet Checklist App Users" list (who can use the Fleet Checklist app, and in which role)
  and registers the people below. Safe to run again: an existing list, column or user
  (same email) is skipped, never changed.

  Roles (each role can do everything the role above it can):
    Driver   - fleet checklist, driver declaration, run sheet
    Reviewer - + Review and sign-off (checklists, run sheets, declarations)
    Admin    - + manages this list (add people, change roles, deactivate leavers)

  How to run:
    1. Check the USERS list below: set each person's role.
    2. Open the Fleet Operations SharePoint site in Edge or Chrome (any page of the site),
       signed in as a site Owner (creating a list needs it).
    3. Press F12, open the Console tab.
    4. Leave DRY_RUN = true for the first run: it only prints what it would do.
    5. Paste this whole file and press Enter. (If the console asks, type "allow pasting" first.)
    6. If the plan looks right, set DRY_RUN = false, paste again and press Enter.
    7. Copy the text it prints (between the ===== lines).
*/
(async () => {
  const DRY_RUN = false;
  const LIST = 'GF Fleet Checklist App Users';

  // [name, email, role]   role: Admin | Reviewer | Driver
  // Only the owner is added for now, so the "App Users – Sync App Access" flow can be tested on one
  // colleague first. Once the flow works, remove the // in front of the others and run again
  // (existing users are skipped).
  const USERS = [
    ['Solomone Tuilagivou', 'solomone.tuilagivou@gfinternational.com.au', 'Admin'],
    // ['Krish Kumar', 'krish.kumar@gfinternational.com.au', 'Reviewer'],
    // ['Pawan Reddy', 'pawan.reddy@gfinternational.com.au', 'Reviewer'],
    // ['Anal Sen', 'anal.sen@gfinternational.com.au', 'Reviewer'],
    // ['Adrian Anthony', 'adrian.anthony@gfinternational.com.au', 'Reviewer'],
    // ['Shahil Kumar', 'shahil.kumar@gfinternational.com.au', 'Reviewer'],
  ];

  // Title (built in) holds the person's name.
  const FIELDS = [
    ['UserEmail', '<Field Type="Text" Name="UserEmail" StaticName="UserEmail" DisplayName="Email" Required="TRUE" MaxLength="255" />'],
    ['AppRole', '<Field Type="Choice" Name="AppRole" StaticName="AppRole" DisplayName="Role" Required="TRUE" Format="Dropdown" FillInChoice="FALSE">' +
      '<Default>Driver</Default><CHOICES><CHOICE>Admin</CHOICE><CHOICE>Reviewer</CHOICE><CHOICE>Driver</CHOICE></CHOICES></Field>'],
    ['ActiveYN', '<Field Type="Boolean" Name="ActiveYN" StaticName="ActiveYN" DisplayName="Active"><Default>1</Default></Field>'],
  ];

  const web = _spPageContextInfo.webAbsoluteUrl;
  const JSON_V = 'application/json;odata=verbose';
  const list = `${web}/_api/web/lists/getbytitle('${encodeURIComponent(LIST)}')`;
  const out = [DRY_RUN ? 'DRY RUN (nothing changed)' : 'CREATING'];
  const digest = (await (await fetch(`${web}/_api/contextinfo`, { method: 'POST', headers: { Accept: JSON_V } })).json())
    .d.GetContextWebInformation.FormDigestValue;
  const post = (url, body) => fetch(url, {
    method: 'POST', headers: { Accept: JSON_V, 'Content-Type': JSON_V, 'X-RequestDigest': digest }, body: JSON.stringify(body),
  });
  const valid = USERS.every(([, e, r]) => /@/.test(e) && ['Admin', 'Reviewer', 'Driver'].includes(r));
  if (!valid) { console.log('Check USERS: every row needs an email and a role of Admin, Reviewer or Driver.'); return; }

  // 1. list
  let listRes = await fetch(`${list}?$select=Title,ListItemEntityTypeFullName`, { headers: { Accept: JSON_V } });
  if (!listRes.ok) {
    if (DRY_RUN) {
      out.push(`would create list "${LIST}" with columns ${FIELDS.map(f => f[0]).join(', ')}`);
      USERS.forEach(([n, e, r]) => out.push(`would add  ${n}  <${e.toLowerCase()}>  ${r}`));
      console.log('=====\n' + out.join('\n') + '\n====='); return;
    }
    const r = await post(`${web}/_api/web/lists`, {
      __metadata: { type: 'SP.List' }, BaseTemplate: 100, Title: LIST,
      Description: 'Who can use the Fleet Checklist app, and their role. Deactivate leavers instead of deleting them.',
    });
    if (!r.ok) { console.log(`Could not create list (${r.status}) ${(await r.text()).slice(0, 300)}`); return; }
    out.push(`created list "${LIST}"`);
    listRes = await fetch(`${list}?$select=Title,ListItemEntityTypeFullName`, { headers: { Accept: JSON_V } });
  } else out.push(`list "${LIST}" already exists`);
  const itemType = (await listRes.json()).d.ListItemEntityTypeFullName;

  // 2. columns
  const have = new Set((await (await fetch(`${list}/fields?$select=InternalName`, { headers: { Accept: JSON_V } })).json())
    .d.results.map(f => f.InternalName));
  for (const [name, xml] of FIELDS) {
    if (have.has(name)) { out.push(`skip column ${name} (exists)`); continue; }
    if (DRY_RUN) { out.push(`would create column ${name}`); continue; }
    const r = await post(`${list}/fields/createfieldasxml`, {
      parameters: { __metadata: { type: 'SP.XmlSchemaFieldCreationInformation' }, SchemaXml: xml, Options: 1 | 8 | 16 },
    });
    out.push(r.ok ? `created column ${name}` : `FAILED column ${name} (${r.status}) ${(await r.text()).slice(0, 200)}`);
  }
  if (!DRY_RUN) { // Title column is labelled "Name" in this list
    await fetch(`${list}/fields/getbyinternalnameortitle('Title')`, {
      method: 'POST', headers: { Accept: JSON_V, 'Content-Type': JSON_V, 'X-RequestDigest': digest, 'X-HTTP-Method': 'MERGE', 'IF-MATCH': '*' },
      body: JSON.stringify({ __metadata: { type: 'SP.Field' }, Title: 'Name' }),
    });
  }

  // 3. users (emails stored in lower case so the app's lookup can run on SharePoint)
  const existing = have.has('UserEmail')
    ? new Set((await (await fetch(`${list}/items?$select=UserEmail&$top=5000`, { headers: { Accept: JSON_V } })).json())
      .d.results.map(i => (i.UserEmail || '').toLowerCase()))
    : new Set();
  for (const [name, email, role] of USERS) {
    const e = email.trim().toLowerCase();
    if (existing.has(e)) { out.push(`skip  ${name} (already registered)`); continue; }
    if (DRY_RUN) { out.push(`would add  ${name}  <${e}>  ${role}`); continue; }
    const r = await post(`${list}/items`, { __metadata: { type: itemType }, Title: name, UserEmail: e, AppRole: role, ActiveYN: true });
    out.push(r.ok ? `added  ${name}  ${role}` : `FAILED ${name} (${r.status}) ${(await r.text()).slice(0, 200)}`);
  }
  console.log('=====\n' + out.join('\n') + '\n=====');
})();
