/*
  Creates the "GF Fleet Checklist Defects" list: one row per checklist item answered No, with the driver's
  comment. Replaces the <field>Cmt comment columns on Fleet Checklist (user's decision, Nov 2026).

  Safe to run again: an existing list, column, index or permission is skipped, never changed.

  What it does:
    1. Creates the list (Title is relabelled "Item": the item's wording) with columns:
         ChecklistID (number: ID of the Fleet Checklist row), Truck (text), ItemField (text: the item's
         internal column name on Fleet Checklist, e.g. field_13), Comment (multi-line plain text)
    2. Indexes ChecklistID and Truck (the app filters on ChecklistID; reports by truck).
    3. Stops inheriting site permissions, COPYING every existing permission first, then grants
         Fleet App Drivers   -> Fleet App Driver   (add and view own; no edit, no delete)
         Fleet App Reviewers -> Fleet App Reviewer (view, add and edit everyone's; no delete)
       and sets item-level permissions to "own items only" (Reviewers see all through the
       Override List Behaviors permission in their level), like the record lists in setup_app_permissions.js.
       The groups and permission levels come from setup_app_permissions.js: run that first.

  How to run:
    1. Open the Fleet Operations SharePoint site in Edge or Chrome, signed in as a site Owner.
    2. Press F12, open the Console tab.
    3. Leave DRY_RUN = true for the first run: it only prints what it would do.
    4. Paste this whole file and press Enter. (If the console asks, type "allow pasting" first.)
    5. If the plan looks right, set DRY_RUN = false, paste again and press Enter.
    6. Copy the text it prints (between the ===== lines).
    7. In Power Apps Studio: Data -> Add data -> SharePoint -> the site -> "GF Fleet Checklist Defects".
*/
(async () => {
  const DRY_RUN = true;
  const LIST = 'GF Fleet Checklist Defects';
  const GROUP_DRIVERS = 'Fleet App Drivers';
  const GROUP_REVIEWERS = 'Fleet App Reviewers';
  const DRIVER_LEVEL = 'Fleet App Driver';
  const REVIEWER_LEVEL = 'Fleet App Reviewer';

  // Title (built in) holds the item's wording.
  const FIELDS = [
    ['ChecklistID', '<Field Type="Number" Name="ChecklistID" StaticName="ChecklistID" DisplayName="Checklist ID" Required="TRUE" Decimals="0" />'],
    ['Truck', '<Field Type="Text" Name="Truck" StaticName="Truck" DisplayName="Truck" MaxLength="255" />'],
    ['ItemField', '<Field Type="Text" Name="ItemField" StaticName="ItemField" DisplayName="Item field" MaxLength="255" />'],
    ['Comment', '<Field Type="Note" Name="Comment" StaticName="Comment" DisplayName="Comment" NumLines="6" RichText="FALSE" />'],
  ];
  const INDEXED = ['ChecklistID', 'Truck'];

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
  const done = () => console.log('=====\n' + out.join('\n') + '\n=====');

  // 1. list
  let info = await get(`${listUrl}?$select=Title,HasUniqueRoleAssignments,ReadSecurity,WriteSecurity`);
  if (!info) {
    if (DRY_RUN) {
      out.push(`would create list "${LIST}" with columns ${FIELDS.map(f => f[0]).join(', ')}`,
        'would relabel Title as "Item"',
        `would index ${INDEXED.join(', ')}`,
        `would stop inheriting (copying all existing permissions); would grant ${GROUP_DRIVERS} -> ${DRIVER_LEVEL}, ` +
        `${GROUP_REVIEWERS} -> ${REVIEWER_LEVEL}; would set item-level "own items only"`);
      done(); return;
    }
    const r = await post(`${web}/_api/web/lists`, {
      __metadata: { type: 'SP.List' }, BaseTemplate: 100, Title: LIST,
      Description: 'Fleet Checklist app: one row per checklist item answered No.',
    });
    if (!r.ok) { await fail(`create list "${LIST}"`, r); done(); return; }
    out.push(`created list "${LIST}"`);
    info = await get(`${listUrl}?$select=Title,HasUniqueRoleAssignments,ReadSecurity,WriteSecurity`);
  } else out.push(`list "${LIST}" already exists`);

  // 2. columns
  const fields = (await get(`${listUrl}/fields?$select=InternalName,Indexed,Title`)).results;
  const have = new Map(fields.map(f => [f.InternalName, f]));
  let created = 0;
  for (const [name, xml] of FIELDS) {
    if (have.has(name)) { out.push(`skip column ${name} (exists)`); continue; }
    if (DRY_RUN) { out.push(`would create column ${name}`); continue; }
    const r = await post(`${listUrl}/fields/createfieldasxml`, {
      parameters: { __metadata: { type: 'SP.XmlSchemaFieldCreationInformation' }, SchemaXml: xml, Options: 1 | 8 | 16 },
    });
    if (r.ok) { out.push(`created column ${name}`); created++; } else await fail(`column ${name}`, r);
  }
  if (have.get('Title')?.Title !== 'Item') {
    if (DRY_RUN) out.push('would relabel Title as "Item"');
    else {
      const r = await merge(`${listUrl}/fields/getbyinternalnameortitle('Title')`, { __metadata: { type: 'SP.Field' }, Title: 'Item' });
      if (r.ok) out.push('relabelled Title as "Item"'); else await fail('relabel Title', r);
    }
  }

  // 3. indexes (re-read: columns created above are not in `have`)
  const nowFields = new Map((await get(`${listUrl}/fields?$select=InternalName,Indexed`)).results.map(f => [f.InternalName, f]));
  for (const name of INDEXED) {
    if (nowFields.get(name)?.Indexed) { out.push(`skip index ${name} (exists)`); continue; }
    if (DRY_RUN) { out.push(`would index ${name}`); continue; }
    const r = await merge(`${listUrl}/fields/getbyinternalnameortitle('${name}')`, { __metadata: { type: 'SP.Field' }, Indexed: true });
    if (r.ok) out.push(`indexed ${name}`); else await fail(`index ${name}`, r);
  }

  // 4. permissions
  const groupId = {};
  for (const g of [GROUP_DRIVERS, GROUP_REVIEWERS]) groupId[g] = (await get(`${web}/_api/web/sitegroups/getbyname('${q(g)}')?$select=Id`))?.Id;
  const levelId = {};
  for (const l of [DRIVER_LEVEL, REVIEWER_LEVEL]) levelId[l] = (await get(`${web}/_api/web/roledefinitions/getbyname('${q(l)}')?$select=Id`))?.Id;
  const grants = [[GROUP_DRIVERS, DRIVER_LEVEL], [GROUP_REVIEWERS, REVIEWER_LEVEL]];
  if (!info.HasUniqueRoleAssignments) {
    if (DRY_RUN) out.push('would stop inheriting (copying all existing permissions)');
    else {
      const r = await post(`${listUrl}/breakroleinheritance(copyRoleAssignments=true,clearSubscopes=false)`);
      if (r.ok) out.push('stopped inheriting (existing permissions copied)'); else await fail('stop inheriting', r);
    }
  } else out.push('list already has its own permissions');
  let granted = 0;
  for (const [group, level] of grants) {
    if (!groupId[group] || !levelId[level]) {
      out.push(`SKIPPED ${group} -> ${level}: group or permission level missing. Run setup_app_permissions.js first, then this again.`);
      continue;
    }
    if (DRY_RUN) { out.push(`would grant ${group} -> ${level}`); continue; }
    // addroleassignment is a no-op when the group already has this level
    const r = await post(`${listUrl}/roleassignments/addroleassignment(principalid=${groupId[group]},roledefid=${levelId[level]})`);
    if (r.ok) { out.push(`${group} -> ${level}`); granted++; } else await fail(`${group} -> ${level}`, r);
  }
  let manual = false;
  if (info.ReadSecurity === 2 && info.WriteSecurity === 2) out.push('skip item-level permissions (already "own items only")');
  else if (DRY_RUN) out.push('would set item-level permissions to "own items only"');
  else {
    const r = await merge(listUrl, { __metadata: { type: 'SP.List' }, ReadSecurity: 2, WriteSecurity: 2 });
    if (r.ok) out.push('item-level permissions set to "own items only"'); else manual = true;
  }
  if (manual) {
    out.push('', 'DO BY HAND (SharePoint would not take this setting from the script):',
      `  ${LIST}: List settings -> Advanced settings -> Item-level Permissions -> ` +
      'Read: "Read items that were created by the user", Create and Edit: "Create items and edit items that were created by the user" -> OK');
  }

  out.push('', `columns created ${created}, groups granted ${granted}${DRY_RUN ? ' (dry run)' : ''}`);
  done();
})();
