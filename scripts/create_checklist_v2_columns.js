/*
  Fleet Checklist v2 columns (checklist redesign, Nov 2026). Source: scripts/checklist_items.json.

  MODE = 'create' (run this first):
    - creates the new Yes/No choice columns: LicenceValid, CabGlassFront, CabGlassRear, CabGlassDriver,
      CabGlassPassenger, CabTilt, AccidentDamage (same type as the existing field_N choice columns:
      Choice, choices Yes / No, no default)
    - indexes field_1 (Truck No) if it isn't indexed yet; the weekly cabin-tilt / greasing check
      filters on it
    Comments on items answered No are not columns: they go in the GF Fleet Checklist Defects list
    (scripts/create_checklist_defects.js). Photo-only items (NetGrossWeight, ProfilePhotos) need no
    column. Columns that already exist
    (same internal name) are skipped, so it is safe to run again.

  MODE = 'rename' (run once Pawan has approved the wording):
    - sets every item's display name to the wording in ITEMS below. The app reads display names
      through DataSourceInfo, so no app change.
      Columns whose display name already matches are skipped.

  ITEMS is generated from scripts/checklist_items.json (field, proposed wording, new Yes/No column?).
  If the JSON changes, update ITEMS to match.

  How to run:
    1. Open the Fleet Operations SharePoint site in Edge or Chrome (any page of the site),
       signed in as someone who can edit the list's columns (site Member or Owner).
    2. Press F12, open the Console tab.
    3. Leave DRY_RUN = true for the first run: it only prints what it would do.
    4. Paste this whole file and press Enter. (If the console asks, type "allow pasting" first.)
    5. If the plan looks right, set DRY_RUN = false, paste again and press Enter.
    6. Copy the text it prints (between the ===== lines).
    7. In Power Apps Studio, refresh the Fleet Checklist data source before pasting scrPreTrip.
*/
(async () => {
  const LIST = 'Fleet Checklist';
  const MODE = 'create';   // 'create' | 'rename'
  const DRY_RUN = true;

  // [internal name, proposed display name, new Yes/No column to create?]
  const ITEMS = [
    ['field_1', "Truck number", false],
    ['field_2', "Driver name", false],
    ['field_3', "Site", false],
    ['LicenceValid', "Valid driver's licence with you", true],
    ['field_50', "Odometer reading (km)", false],
    ['NextServiceDue', "Next service due (km)", false],
    ['field_23', "Cabin doors open, close and lock", false],
    ['field_24', "Front / rear windscreens free of cracks", false],
    ['CabGlassFront', "Front windscreen free of cracks and chips", true],
    ['CabGlassRear', "Rear cabin window free of cracks", true],
    ['CabGlassDriver', "Driver's window uncracked and winds freely", true],
    ['CabGlassPassenger', "Passenger's window uncracked and winds freely", true],
    ['field_25', "Mirrors clean, uncracked and adjusted", false],
    ['field_26', "Both seat belts lock and release", false],
    ['field_21', "Dashboard gauges and warning lights working", false],
    ['AccCabinClean', "Cabin clean and tidy", false],
    ['AccMats', "Floor mats in cabin", false],
    ['CabTilt', "Cabin tilt inspection done", true],
    ['field_10', "Battery water at top mark", false],
    ['field_11', "Battery terminals tight and clean", false],
    ['field_12', "Battery isolator switch working", false],
    ['field_13', "Headlights and fog lights working", false],
    ['field_14', "All indicators working", false],
    ['field_15', "Brake lights working", false],
    ['field_16', "Reverse alarm and lights working", false],
    ['field_17', "Cabin interior light working", false],
    ['field_18', "Rear spotlight working", false],
    ['field_19', "Horn working", false],
    ['field_20', "Truck and bin cables undamaged", false],
    ['field_22', "Electrical comments", false],
    ['field_32', "Tyres good, no steer-wheel retreads", false],
    ['field_33', "All wheel nuts and studs present", false],
    ['field_34', "Spare tyre in good condition", false],
    ['field_35', "Jack and wheel brace present and working", false],
    ['field_36', "Brakes and tyres comments", false],
    ['field_7', "No oil or water leaks", false],
    ['field_4', "Engine and hydraulic oil at top level", false],
    ['field_5', "Coolant at top mark", false],
    ['field_31', "Air hoses not leaking or damaged", false],
    ['field_6', "Fan belts tight and in good condition", false],
    ['field_9', "Engine comments", false],
    ['field_27', "Springs, U-bolts and bin bolts secure", false],
    ['field_28', "Front and rear bumpers secure", false],
    ['field_8', "PTO working with no leaks", false],
    ['field_29', "Body comments", false],
    ['field_30', "Foot brake and park brake working", false],
    ['field_37', "Cones and reflector triangle in truck", false],
    ['field_38', "Your PPE with you", false],
    ['field_39', "Fire extinguisher in place and in date", false],
    ['field_40', "First aid box in truck and stocked", false],
    ['field_41', "Torch working", false],
    ['field_42', "Raincoat and helmet in truck", false],
    ['field_43', "Safety comments", false],
    ['field_44', "Underneath greasing done", false],
    ['field_45', "Wheel chocks in truck", false],
    ['field_46', "Freezer and dry box locked", false],
    ['field_47', "Money bag and lock in truck", false],
    ['field_48', "Money box in the truck?", false],
    ['field_49', "General comments", false],
    ['AccCOFExpiry', "COF expiry date", false],
    ['AccBlowerServiceDue', "Blower service due date", false],
    ['AccTruckServiceDue', "Truck service due date", false],
    ['AccSpareTyre', "Spare tyre in truck", false],
    ['AccTyreCondition', "Every tyre in good condition", false],
    ['AccFireExtinguisher', "Fire extinguisher mounted and serviceable", false],
    ['AccFirstAidKit', "First aid kit in truck", false],
    ['AccTrafficCones', "Traffic cones in truck", false],
    ['AccFuelCard', "Fuel card in truck", false],
    ['AccPlugWire', "Fridge plug-in lead in truck", false],
    ['AccEngJack', "Engraved jack in truck", false],
    ['AccEngWheelBrace', "Engraved wheel brace in truck", false],
    ['AccEngPipe', "Engraved pipe in truck", false],
    ['AccEngTyreWinder', "Engraved spare-tyre winder in truck", false],
    ['AccEngTrolley', "Engraved trolley in truck", false],
    ['AccTruckFloor', "Load floor clean and undamaged", false],
    ['AccComments', "Accessory comments", false],
    ['AccidentDamage', "No new dents or cracks", true],
    ['field_51', "Other comments", false],
  ];
  const INDEX_FIELDS = ['field_1'];

  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const schema = (name, title, kind) => {
    const common = `Name="${name}" StaticName="${name}" DisplayName="${esc(title)}" Required="FALSE"`;
    // Yes/No choice: no default, single select, no fill-in values (same as the field_N columns)
    return `<Field Type="Choice" ${common} Format="Dropdown" FillInChoice="FALSE">` +
      '<CHOICES><CHOICE>Yes</CHOICE><CHOICE>No</CHOICE></CHOICES></Field>';
  };

  const web = _spPageContextInfo.webAbsoluteUrl;
  const q = s => encodeURIComponent(s.replace(/'/g, "''"));
  const list = `${web}/_api/web/lists/getbytitle('${q(LIST)}')`;
  const V = 'application/json;odata=verbose';
  const out = [];

  const existingRes = await fetch(`${list}/fields?$select=InternalName,Title,Indexed`, { headers: { Accept: V } });
  if (!existingRes.ok) { console.log(`List "${LIST}" not found or no access (${existingRes.status})`); return; }
  const existing = new Map((await existingRes.json()).d.results.map(f => [f.InternalName, f]));

  const digest = (await (await fetch(`${web}/_api/contextinfo`, { method: 'POST', headers: { Accept: V } })).json())
    .d.GetContextWebInformation.FormDigestValue;
  const post = (url, body, extra = {}) => fetch(url, {
    method: 'POST', headers: { Accept: V, 'Content-Type': V, 'X-RequestDigest': digest, ...extra },
    body: JSON.stringify(body),
  });
  const mergeField = (name, props) => post(`${list}/fields/getbyinternalnameortitle('${q(name)}')`,
    { __metadata: { type: 'SP.Field' }, ...props }, { 'X-HTTP-Method': 'MERGE', 'IF-MATCH': '*' });

  out.push(`${DRY_RUN ? 'DRY RUN (nothing changed)' : 'CHANGING'}  mode "${MODE}" on list "${LIST}"`);
  let done = 0, skipped = 0, failed = 0;

  if (MODE === 'create') {
    const wanted = [];
    for (const [name, title, isNewChoice] of ITEMS) {
      if (isNewChoice) wanted.push([name, title, 'yesno']);
    }
    for (const [name, title, kind] of wanted) {
      if (existing.has(name)) { out.push(`skip    ${name}  (already exists as "${existing.get(name).Title}")`); skipped++; continue; }
      if (DRY_RUN) { out.push(`would create  ${name}  "${title}"  ${kind}`); continue; }
      const r = await post(`${list}/fields/createfieldasxml`, {
        parameters: {
          __metadata: { type: 'SP.XmlSchemaFieldCreationInformation' },
          SchemaXml: schema(name, title, kind),
          Options: 1 | 8 | 16, // default content type + keep internal name + add to default view
        },
      });
      if (!r.ok) { out.push(`FAILED  ${name}  (${r.status}) ${(await r.text()).slice(0, 200)}`); failed++; continue; }
      const f = (await r.json()).d;
      const ok = f.InternalName === name;
      out.push(`${ok ? 'created' : 'CHECK  '} ${f.InternalName}  "${f.Title}"  ${f.TypeAsString}` +
        (ok ? '' : `   <-- expected internal name ${name}`));
      if (ok) done++; else failed++;
    }
    for (const name of INDEX_FIELDS) {
      const f = existing.get(name);
      if (!f) { out.push(`FAILED  index ${name}: column not found`); failed++; continue; }
      if (f.Indexed) { out.push(`skip    index ${name}  (already indexed)`); continue; }
      if (DRY_RUN) { out.push(`would index  ${name}  "${f.Title}"`); continue; }
      const r = await mergeField(name, { Indexed: true });
      out.push(r.ok ? `indexed ${name}  "${f.Title}"` : `FAILED  index ${name} (${r.status}) ${(await r.text()).slice(0, 200)}`);
      if (!r.ok) failed++;
    }
  } else if (MODE === 'rename') {
    for (const [name, title] of ITEMS) {
      const f = existing.get(name);
      if (!f) { out.push(`MISSING ${name}  (run MODE = 'create' first)`); failed++; continue; }
      if (f.Title === title) { out.push(`skip    ${name}  (already "${title}")`); skipped++; continue; }
      if (DRY_RUN) { out.push(`would rename  ${name}  "${f.Title}"  ->  "${title}"`); continue; }
      const r = await mergeField(name, { Title: title });
      if (r.ok) { out.push(`renamed ${name}  "${f.Title}"  ->  "${title}"`); done++; }
      else { out.push(`FAILED  ${name}  (${r.status}) ${(await r.text()).slice(0, 200)}`); failed++; }
    }
  } else {
    out.push(`Unknown MODE "${MODE}". Use 'create' or 'rename'.`);
  }

  out.push('', `${MODE === 'create' ? 'created' : 'renamed'} ${done}, skipped ${skipped}, problems ${failed}`);
  console.log('=====\n' + out.join('\n') + '\n=====');
})();
