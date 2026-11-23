/*
  One-time setup for app-managed access to the Fleet Checklist lists.

  After this has run, an Admin adds people in the app (Manage users screen). The "SyncAppUser" flow then
  writes the App Users row and puts the person in the right SharePoint group below. Adding someone to a
  group this way sends no email.

  What it does (safe to run again; anything that already exists is skipped):
    1. Creates two permission levels:
         Fleet App Driver    - add items, and view (SharePoint won't allow add without view; item-level
                               permissions below limit that to their own). No edit, no delete.
         Fleet App Reviewer  - view, add and edit items, plus "Override List Behaviors", so reviewers see
                               and sign off everyone's records. No delete.
    2. Creates two SharePoint groups (members can't see who else is in them):
         Fleet App Drivers    <- people with role Driver
         Fleet App Reviewers  <- people with role Reviewer or Admin
    3. On the four record lists (Fleet Checklist, Run Sheets, Run Sheet Details, Driver Declarations):
         - stops inheriting site permissions, COPYING every existing permission first, so the site
           Owners group, the flow owner and everyone who has access today keep it. (The 2 Nov problem
           came from losing existing permissions. Copying keeps them.)
         - grants Fleet App Drivers -> Fleet App Driver, Fleet App Reviewers -> Fleet App Reviewer
         - turns on item-level permissions: "read only items created by the user"
           (if SharePoint refuses this through the script, it prints the two clicks to do by hand)
    4. On GF Fleet Checklist App Users: grants both groups Read (the app reads it at start-up).
    5. Puts everyone already in App Users (Active = Yes) into the right group.

  How to run:
    1. Open the Fleet Operations SharePoint site in Edge or Chrome, signed in as a site Owner.
    2. Press F12, open the Console tab.
    3. Leave DRY_RUN = true for the first run: it only prints what it would do.
    4. Paste this whole file and press Enter. (If the console asks, type "allow pasting" first.)
    5. If the plan looks right, set DRY_RUN = false, paste again and press Enter.
    6. Copy the text it prints (between the ===== lines).
*/
(async () => {
  const DRY_RUN = true;

  const RECORD_LISTS = ['Fleet Checklist', 'Run Sheets', 'Run Sheet Details', 'Driver Declarations'];
  const USERS_LIST = 'GF Fleet Checklist App Users';
  const GROUP_DRIVERS = 'Fleet App Drivers';
  const GROUP_REVIEWERS = 'Fleet App Reviewers';

  // SP.PermissionKind numbers (1-based bit positions)
  const VIEW_ITEMS = 1, ADD_ITEMS = 2, EDIT_ITEMS = 3, OPEN_ITEMS = 6, OVERRIDE_LIST_BEHAVIORS = 9,
    VIEW_FORM_PAGES = 13, OPEN = 17, VIEW_PAGES = 18, BROWSE_USER_INFO = 28,
    USE_CLIENT_INTEGRATION = 37, USE_REMOTE_APIS = 38;
  const DRIVER_KINDS = [VIEW_ITEMS, ADD_ITEMS, OPEN_ITEMS, VIEW_FORM_PAGES, OPEN, VIEW_PAGES,
    BROWSE_USER_INFO, USE_CLIENT_INTEGRATION, USE_REMOTE_APIS];
  const LEVELS = [
    { name: 'Fleet App Driver', kinds: DRIVER_KINDS, order: 180,
      desc: 'Fleet Checklist app drivers: add items and view their own. No edit, no delete.' },
    { name: 'Fleet App Reviewer', kinds: [...DRIVER_KINDS, EDIT_ITEMS, OVERRIDE_LIST_BEHAVIORS], order: 181,
      desc: 'Fleet Checklist app reviewers: view, add and edit everyone\'s items.' },
  ];
  const GROUPS = [
    { name: GROUP_DRIVERS, level: 'Fleet App Driver', desc: 'Fleet Checklist app: Drivers. Managed by the app; don\'t edit by hand.' },
    { name: GROUP_REVIEWERS, level: 'Fleet App Reviewer', desc: 'Fleet Checklist app: Reviewers and Admins. Managed by the app; don\'t edit by hand.' },
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
  const mask = kinds => {
    let low = 0, high = 0;
    for (const k of kinds) { if (k <= 32) low += 2 ** (k - 1); else high += 2 ** (k - 33); }
    return { Low: String(low), High: String(high) };
  };

  // 1. permission levels
  const roleId = {};
  for (const l of LEVELS) {
    const have = await get(`${web}/_api/web/roledefinitions/getbyname('${q(l.name)}')?$select=Id`);
    if (have) { roleId[l.name] = have.Id; out.push(`skip permission level "${l.name}" (exists)`); continue; }
    if (DRY_RUN) { out.push(`would create permission level "${l.name}"`); continue; }
    const r = await post(`${web}/_api/web/roledefinitions`, {
      __metadata: { type: 'SP.RoleDefinition' }, Name: l.name, Description: l.desc, Order: l.order,
      BasePermissions: { __metadata: { type: 'SP.BasePermissions' }, ...mask(l.kinds) },
    });
    if (!r.ok) { await fail(`permission level "${l.name}" (if this says the site inherits permission levels, run the script on the parent site)`, r); continue; }
    roleId[l.name] = (await r.json()).d.Id;
    out.push(`created permission level "${l.name}"`);
  }
  const readId = (await get(`${web}/_api/web/roledefinitions/getbytype(2)?$select=Id`))?.Id; // 2 = Reader

  // 2. groups
  const groupId = {};
  for (const g of GROUPS) {
    const have = await get(`${web}/_api/web/sitegroups/getbyname('${q(g.name)}')?$select=Id`);
    if (have) { groupId[g.name] = have.Id; out.push(`skip group "${g.name}" (exists)`); continue; }
    if (DRY_RUN) { out.push(`would create group "${g.name}"`); continue; }
    const r = await post(`${web}/_api/web/sitegroups`, {
      __metadata: { type: 'SP.Group' }, Title: g.name, Description: g.desc,
      OnlyAllowMembersViewMembership: true, AllowMembersEditMembership: false, AllowRequestToJoinLeave: false,
    });
    if (!r.ok) { await fail(`group "${g.name}"`, r); continue; }
    groupId[g.name] = (await r.json()).d.Id;
    out.push(`created group "${g.name}" (owner: you)`);
  }

  // 3. record lists
  const manual = [];
  for (const title of RECORD_LISTS) {
    const listUrl = `${web}/_api/web/lists/getbytitle('${q(title)}')`;
    const info = await get(`${listUrl}?$select=Title,HasUniqueRoleAssignments`);
    if (!info) { out.push(`FAILED list "${title}" not found. Check the name.`); continue; }
    if (DRY_RUN) {
      out.push(`${title}: ${info.HasUniqueRoleAssignments ? 'already has its own permissions' : 'would stop inheriting (copying all existing permissions)'}; ` +
        `would grant ${GROUP_DRIVERS} -> Fleet App Driver, ${GROUP_REVIEWERS} -> Fleet App Reviewer; would set item-level "own items only"`);
      continue;
    }
    if (!info.HasUniqueRoleAssignments) {
      const r = await post(`${listUrl}/breakroleinheritance(copyRoleAssignments=true,clearSubscopes=false)`);
      if (!r.ok) { await fail(`${title}: stop inheriting`, r); continue; }
      out.push(`${title}: stopped inheriting (existing permissions copied)`);
    }
    for (const g of GROUPS) {
      if (!groupId[g.name] || !roleId[g.level]) { out.push(`${title}: skipped ${g.name} (group or level missing)`); continue; }
      const r = await post(`${listUrl}/roleassignments/addroleassignment(principalid=${groupId[g.name]},roledefid=${roleId[g.level]})`);
      out.push(r.ok ? `${title}: ${g.name} -> ${g.level}` : `FAILED ${title}: ${g.name} (${r.status})`);
    }
    const r = await post(listUrl, { __metadata: { type: 'SP.List' }, ReadSecurity: 2, WriteSecurity: 2 },
      { 'X-HTTP-Method': 'MERGE', 'IF-MATCH': '*' });
    if (r.ok) out.push(`${title}: item-level permissions set to "own items only"`);
    else manual.push(title);
  }

  // 4. App Users list: Read for both groups
  const usersUrl = `${web}/_api/web/lists/getbytitle('${q(USERS_LIST)}')`;
  if (DRY_RUN) out.push(`${USERS_LIST}: would grant both groups Read`);
  else for (const g of GROUPS) {
    if (!groupId[g.name] || !readId) continue;
    const r = await post(`${usersUrl}/roleassignments/addroleassignment(principalid=${groupId[g.name]},roledefid=${readId})`);
    out.push(r.ok ? `${USERS_LIST}: ${g.name} -> Read` : `FAILED ${USERS_LIST}: ${g.name} (${r.status}). Is the list name right?`);
  }

  // 5. existing app users into groups
  const rows = (await get(`${usersUrl}/items?$select=Title,UserEmail,AppRole,ActiveYN&$top=5000`))?.results || [];
  for (const u of rows.filter(x => x.ActiveYN)) {
    const email = (u.UserEmail || '').trim().toLowerCase();
    const group = u.AppRole === 'Driver' ? GROUP_DRIVERS : GROUP_REVIEWERS;
    if (!email) continue;
    if (DRY_RUN) { out.push(`would add ${u.Title} (${u.AppRole}) to ${group}`); continue; }
    const r = await post(`${web}/_api/web/sitegroups/getbyname('${q(group)}')/users`,
      { __metadata: { type: 'SP.User' }, LoginName: `i:0#.f|membership|${email}` });
    out.push(r.ok ? `added ${u.Title} to ${group}` : `FAILED adding ${u.Title} to ${group} (${r.status})`);
  }

  if (manual.length) {
    out.push('', 'DO BY HAND (SharePoint would not take this setting from the script):');
    for (const t of manual) out.push(`  ${t}: List settings -> Advanced settings -> Item-level Permissions -> ` +
      'Read: "Read items that were created by the user", Create and Edit: "Create items and edit items that were created by the user" -> OK');
  }
  console.log('=====\n' + out.join('\n') + '\n=====');
})();
