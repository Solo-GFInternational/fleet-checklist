/*
  Fleet Checklist v2 columns (checklist redesign, Nov 2026). Source: scripts/checklist_items.json.

  MODE = 'create' (run this first):
    - creates the new Yes/No choice columns: LicenceValid, CabGlassFront, CabGlassRear, CabGlassDriver,
      CabGlassPassenger, CabTilt, AccidentDamage (same type as the existing field_N choice columns:
      Choice, choices Yes / No, no default)
    - creates one multi-line plain-text comment column <field>Cmt per Yes/No item
      (display name "<item wording> – comment")
    - indexes field_1 (Truck No) if it isn't indexed yet; the weekly cabin-tilt / greasing check
      filters on it
    Photo-only items (NetGrossWeight, ProfilePhotos) need no column. Columns that already exist
    (same internal name) are skipped, so it is safe to run again.

  MODE = 'rename' (run once Pawan has approved the wording):
    - sets every item's display name to the wording in ITEMS below, and each comment column to
      "<wording> – comment". The app reads display names through DataSourceInfo, so no app change.
      Columns whose display name already matches are skipped.

  ITEMS is generated from scripts/checklist_items.json (field, proposed wording, new Yes/No column?,
  comment column). If the JSON changes, update ITEMS to match.

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

  // [internal name, proposed display name, new Yes/No column to create?, comment column or null]
  const ITEMS = [
    ['field_1', "Truck number", false, null],
    ['field_2', "Driver name", false, null],
    ['field_3', "Site", false, null],
    ['LicenceValid', "Do you have a valid driver's licence with you?", true, 'LicenceValidCmt'],
    ['field_50', "Odometer reading (km)", false, null],
    ['NextServiceDue', "Next service due (km)", false, null],
    ['field_23', "Cabin doors and locks working?", false, 'field_23Cmt'],
    ['field_24', "Front / rear windscreens free of cracks", false, null],
    ['CabGlassFront', "Front windscreen free of cracks and chips?", true, 'CabGlassFrontCmt'],
    ['CabGlassRear', "Rear cabin window free of cracks?", true, 'CabGlassRearCmt'],
    ['CabGlassDriver', "Driver's door window free of cracks and working?", true, 'CabGlassDriverCmt'],
    ['CabGlassPassenger', "Passenger's door window free of cracks and working?", true, 'CabGlassPassengerCmt'],
    ['field_25', "Mirrors clean, uncracked and set for you?", false, 'field_25Cmt'],
    ['field_26', "Both seat belts working?", false, 'field_26Cmt'],
    ['field_21', "Dashboard gauges and warning lights working?", false, 'field_21Cmt'],
    ['AccCabinClean', "Cabin clean and tidy?", false, 'AccCabinCleanCmt'],
    ['AccMats', "Floor mats in the cabin?", false, 'AccMatsCmt'],
    ['CabTilt', "Cabin tilting", true, 'CabTiltCmt'],
    ['field_10', "Battery water at the top mark?", false, 'field_10Cmt'],
    ['field_11', "Battery terminals tight and clean?", false, 'field_11Cmt'],
    ['field_12', "Battery isolator switch working?", false, 'field_12Cmt'],
    ['field_13', "Headlights and fog lights working?", false, 'field_13Cmt'],
    ['field_14', "All indicators working?", false, 'field_14Cmt'],
    ['field_15', "Brake lights working?", false, 'field_15Cmt'],
    ['field_16', "Reverse alarm and reverse lights working?", false, 'field_16Cmt'],
    ['field_17', "Cabin interior light working?", false, 'field_17Cmt'],
    ['field_18', "Rear spotlight working?", false, 'field_18Cmt'],
    ['field_19', "Horn working?", false, 'field_19Cmt'],
    ['field_20', "Truck and bin electrical cables undamaged?", false, 'field_20Cmt'],
    ['field_22', "Electrical comments", false, null],
    ['field_32', "Tyres in good condition?", false, 'field_32Cmt'],
    ['field_33', "All wheel nuts and studs in place?", false, 'field_33Cmt'],
    ['field_34', "Spare tyre in good condition?", false, 'field_34Cmt'],
    ['field_35', "Jack and wheel brace in the truck and working?", false, 'field_35Cmt'],
    ['field_36', "Brakes and tyres comments", false, null],
    ['field_7', "No oil or water leaks?", false, 'field_7Cmt'],
    ['field_4', "Engine and hydraulic oil at the top level?", false, 'field_4Cmt'],
    ['field_5', "Coolant at the top mark?", false, 'field_5Cmt'],
    ['field_31', "Air hoses free of leaks and damage?", false, 'field_31Cmt'],
    ['field_6', "Fan belts in good condition and tight?", false, 'field_6Cmt'],
    ['field_9', "Engine comments", false, null],
    ['field_27', "Springs, U-bolts and bin bolts secure?", false, 'field_27Cmt'],
    ['field_28', "Front and rear bumpers secure and undamaged?", false, 'field_28Cmt'],
    ['field_8', "PTO working with no leaks?", false, 'field_8Cmt'],
    ['field_29', "Body comments", false, null],
    ['field_30', "Foot brake and park brake working?", false, 'field_30Cmt'],
    ['field_37', "Cones and reflector triangle in the truck?", false, 'field_37Cmt'],
    ['field_38', "Your PPE with you?", false, 'field_38Cmt'],
    ['field_39', "Fire extinguisher in place and in date?", false, 'field_39Cmt'],
    ['field_40', "First aid box in the truck and stocked?", false, 'field_40Cmt'],
    ['field_41', "Torch working?", false, 'field_41Cmt'],
    ['field_42', "Raincoat and helmet in the truck?", false, 'field_42Cmt'],
    ['field_43', "Safety comments", false, null],
    ['field_44', "Underneath greasing", false, 'field_44Cmt'],
    ['field_45', "Wheel chocks in the truck?", false, 'field_45Cmt'],
    ['field_46', "Freezer and dry box locked?", false, 'field_46Cmt'],
    ['field_47', "Money bag and lock in the truck?", false, 'field_47Cmt'],
    ['field_48', "Money box in the truck?", false, null],
    ['field_49', "General comments", false, null],
    ['AccCOFExpiry', "COF expiry date", false, null],
    ['AccBlowerServiceDue', "Blower service due date", false, null],
    ['AccTruckServiceDue', "Truck service due date", false, null],
    ['AccSpareTyre', "Spare tyre in the truck?", false, 'AccSpareTyreCmt'],
    ['AccTyreCondition', "Tyre condition (photo of every tyre)", false, 'AccTyreConditionCmt'],
    ['AccFireExtinguisher', "Fire extinguisher mounted and serviceable?", false, 'AccFireExtinguisherCmt'],
    ['AccFirstAidKit', "First aid kit in the truck?", false, 'AccFirstAidKitCmt'],
    ['AccTrafficCones', "Traffic cones in the truck?", false, 'AccTrafficConesCmt'],
    ['AccFuelCard', "Fuel card in the truck?", false, 'AccFuelCardCmt'],
    ['AccPlugWire', "Fridge plug-in lead in the truck?", false, 'AccPlugWireCmt'],
    ['AccEngJack', "Engraved jack in the truck?", false, 'AccEngJackCmt'],
    ['AccEngWheelBrace', "Engraved wheel brace in the truck?", false, 'AccEngWheelBraceCmt'],
    ['AccEngPipe', "Engraved pipe in the truck?", false, 'AccEngPipeCmt'],
    ['AccEngTyreWinder', "Engraved spare-tyre winder in the truck?", false, 'AccEngTyreWinderCmt'],
    ['AccEngTrolley', "Engraved trolley in the truck?", false, 'AccEngTrolleyCmt'],
    ['AccTruckFloor', "Load floor clean and undamaged?", false, 'AccTruckFloorCmt'],
    ['AccComments', "Accessory comments", false, null],
    ['AccidentDamage', "Any new dents or cracks?", true, 'AccidentDamageCmt'],
    ['field_51', "Other comments", false, null],
  ];
  const INDEX_FIELDS = ['field_1'];
  const cmtTitle = name => `${name} – comment`;

  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const schema = (name, title, kind) => {
    const common = `Name="${name}" StaticName="${name}" DisplayName="${esc(title)}" Required="FALSE"`;
    if (kind === 'note') return `<Field Type="Note" ${common} NumLines="6" RichText="FALSE" AppendOnly="FALSE" />`;
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
    for (const [name, title, isNewChoice, cmt] of ITEMS) {
      if (isNewChoice) wanted.push([name, title, 'yesno']);
      if (cmt) wanted.push([cmt, cmtTitle(title), 'note']);
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
    const wanted = [];
    for (const [name, title, , cmt] of ITEMS) {
      wanted.push([name, title]);
      if (cmt) wanted.push([cmt, cmtTitle(title)]);
    }
    for (const [name, title] of wanted) {
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
