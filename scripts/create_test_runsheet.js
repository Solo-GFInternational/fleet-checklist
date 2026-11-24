/*
  Creates a TEST run the way the app sends one, including invoice photos, to test the
  "Run Sheet - Submission email" flow (wait loop, invoice photos attached to the email, and the
  link to the run's photos in Fleet Photos).

  What it creates, in the app's order:
    1. The trip in Run Sheets, once, already submitted: Status "Open", Time returned and End mileage
       filled in, plus NoofStops, NoofInvoicePhotos and RunKey. This starts the flow straight away.
    2. The stops in Run Sheet Details, linked by the RunSheet lookup AND the RunSheetID number.
    3. Invoice photos in Fleet Photos: generated JPEGs (a coloured "TEST INVOICE" page per photo),
       tagged like SaveFleetPhotos tags them (Truck, PhotoType "Invoice", Item "Stop N · Invoice k",
       RecordID = stop ID, SourceList "Run Sheet Details", RunKey, StopKey).
       PHOTOS_FIRST = true uploads them before the trip, as the app does when it has signal (RecordID 0).
       PHOTOS_FIRST = false uploads them PHOTO_DELAY_SECONDS after the stops, so the flow has to wait.
       RETAKE = true adds a second, newer copy of stop 1's first photo: the email must attach only the retake.

  The photos go straight into the library, so this tests the submission email flow, not SaveFleetPhotos.

  The stops include one of each case the emails flag:
    - a stop warmer than -15 °C              (⚠ in the submission email)
    - a stop that took over 15 min to unload (⚠ in the submission email)
    - a stop where Actual Quantity ≠ Total Quantity, with a reason (Trade Issue email),
      only if the TotalQty / ActualQty / TradeIssueReason columns exist.

  Everything is marked as a test (comments "AUTOMATED TEST", photos say TEST INVOICE, the truck is one of
  the 9 test registrations, RunKey starts with "TEST-"), so it's easy to find and delete.

  How to run:
    1. Open the Fleet Operations SharePoint site in Edge or Chrome.
    2. F12 → Console, paste this whole file, Enter. (Type "allow pasting" first if asked.)
    3. Leave DRY_RUN = true the first time: it prints what it would create.
    4. Set DRY_RUN = false and run again. Copy the text between the ===== lines if anything fails.
    5. Keep the tab open until it prints the closing ===== line (photo uploads take a few seconds each).
*/
(async () => {
  // ------------------------------------------------------------------ SETTINGS
  const DRY_RUN = true;
  const STOPS = 5;                 // how many stops (3 or more, so every test case is included)
  const PHOTOS_PER_STOP = 2;       // invoice photos per stop (0 = none); the app allows up to 20
  const PHOTOS_FIRST = false;      // true = photos before the trip (as the app); false = late, tests the wait
  const PHOTO_DELAY_SECONDS = 60;  // with PHOTOS_FIRST = false: pause between the stops and the photos
  const RETAKE = true;             // add a newer copy of stop 1 / invoice 1
  const PHOTO_WIDTH = 1200, PHOTO_HEIGHT = 1600, JPEG_QUALITY = 0.8;   // about 100–200 KB each
  const RUNS = 'Run Sheets';
  const STOPS_LIST = 'Run Sheet Details';
  const PHOTOS = 'Fleet Photos';
  // Test registrations from files/Fiji Number Plate QR Codes samples.docx; one is picked at random each run.
  const TRUCKS = ['FJ 101', 'CA 203', 'KI 123', 'LA 456', 'HX 789', 'GV 312', 'EF 645', 'JK 908', 'BN 274'];
  const TRUCK = TRUCKS[Math.floor(Math.random() * TRUCKS.length)];
  // ------------------------------------------------------------------

  const web = _spPageContextInfo.webAbsoluteUrl;
  const me = _spPageContextInfo.userDisplayName || 'Test Driver';
  const J = 'application/json;odata=verbose';
  // every line is printed straight away (so you can see progress) and again in the summary at the end
  const out = [];
  out.push = (...lines) => { lines.forEach(l => console.log(l)); return Array.prototype.push.apply(out, lines); };
  if (DRY_RUN) console.warn('DRY RUN: nothing will be created. Set DRY_RUN = false near the top and paste again to create the test run.');
  out.push(DRY_RUN ? 'DRY RUN (nothing created)' : 'CREATING TEST RUN (keep this tab open until the closing ===== line)');
  const enc = s => encodeURIComponent(s.replace(/'/g, "''"));
  const list = t => `${web}/_api/web/lists/getbytitle('${enc(t)}')`;
  const get = async url => { const r = await fetch(url, { headers: { Accept: J } }); if (!r.ok) throw new Error(`${r.status} ${url}`); return (await r.json()).d; };
  const digest = (await (await fetch(`${web}/_api/contextinfo`, { method: 'POST', headers: { Accept: J } })).json())
    .d.GetContextWebInformation.FormDigestValue;
  const send = (url, body, merge) => fetch(url, { method: 'POST', body: JSON.stringify(body),
    headers: Object.assign({ Accept: J, 'Content-Type': J, 'X-RequestDigest': digest }, merge ? { 'X-HTTP-Method': 'MERGE', 'IF-MATCH': '*' } : {}) });
  const columns = async t => Object.fromEntries((await get(`${list(t)}/fields?$filter=Hidden eq false&$select=InternalName,TypeAsString`))
    .results.map(f => [f.InternalName, f.TypeAsString]));
  // keep only the values whose column exists
  const only = (cols, obj) => Object.fromEntries(Object.entries(obj).filter(([k]) => k === '__metadata' || (k in cols) || (k.endsWith('Id') && (k.slice(0, -2) in cols))));
  const hhmm = (h, m) => `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  const sleep = s => new Promise(r => setTimeout(r, s * 1000));
  const stamp = () => new Date().toISOString().replace(/\D/g, '').slice(0, 17);   // yyyyMMddHHmmssfff
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const runKey = 'TEST-' + crypto.randomUUID();
  const COLOURS = ['#E2F3F2', '#FFF4C2', '#E6F2D6', '#D9F4FA', '#F3E6F7', '#FDE7DC'];

  // A plain "invoice" page as a JPEG Blob: coloured background, header, a few fake lines.
  const invoiceJpeg = (stopNo, slot, retake) => new Promise(resolve => {
    const c = document.createElement('canvas');
    c.width = PHOTO_WIDTH; c.height = PHOTO_HEIGHT;
    const g = c.getContext('2d'), W = PHOTO_WIDTH, u = W / 100;
    g.fillStyle = retake ? '#FFD6D6' : COLOURS[(stopNo - 1) % COLOURS.length]; g.fillRect(0, 0, W, PHOTO_HEIGHT);
    g.fillStyle = '#FFFFFF'; g.fillRect(6 * u, 6 * u, W - 12 * u, PHOTO_HEIGHT - 12 * u);
    g.fillStyle = '#089090'; g.fillRect(6 * u, 6 * u, W - 12 * u, 14 * u);
    g.fillStyle = '#FFFFFF'; g.font = `bold ${7 * u}px Arial`; g.fillText(retake ? 'TEST INVOICE (RETAKE)' : 'TEST INVOICE', 10 * u, 15.5 * u);
    g.fillStyle = '#1F2933'; g.font = `bold ${5 * u}px Arial`;
    g.fillText(`Stop ${stopNo} · Invoice ${slot}`, 10 * u, 30 * u);
    g.font = `${3.6 * u}px Arial`; g.fillStyle = '#606C76';
    [`Truck: ${TRUCK}`, `Customer: Test Customer ${stopNo}`, `Invoice no: TEST-${stopNo}-${slot}`,
     `Date: ${today.toDateString()}`, `Run key: ${runKey.slice(0, 13)}…`].forEach((t, i) => g.fillText(t, 10 * u, (38 + i * 5.5) * u));
    g.strokeStyle = '#D0D8DA'; g.lineWidth = u / 4;
    for (let i = 0; i < 8; i++) {
      const y = (72 + i * 7) * u;
      g.beginPath(); g.moveTo(10 * u, y); g.lineTo(W - 10 * u, y); g.stroke();
      g.fillStyle = '#1F2933'; g.fillText(`Item ${i + 1}   ${(i + 1) * stopNo} ctn`, 10 * u, y - 2 * u);
    }
    g.fillStyle = '#089090'; g.font = `bold ${4 * u}px Arial`; g.fillText('AUTOMATED TEST – NOT A REAL INVOICE', 10 * u, PHOTO_HEIGHT - 12 * u);
    c.toBlob(resolve, 'image/jpeg', JPEG_QUALITY);
  });

  try {
    const runInfo = await get(`${list(RUNS)}?$select=ListItemEntityTypeFullName`);
    const stopInfo = await get(`${list(STOPS_LIST)}?$select=ListItemEntityTypeFullName`);
    const runCols = await columns(RUNS);
    const stopCols = await columns(STOPS_LIST);
    if (!('RunSheetID' in stopCols)) out.push('note: Run Sheet Details has no RunSheetID column – the app and the submission email need it');
    ['NoofStops', 'NoofInvoicePhotos', 'RunKey'].forEach(k => { if (!(k in runCols)) out.push(`note: Run Sheets has no ${k} column – run scripts/create_runsheet_v2_columns.js first`); });

    let photoInfo = null, photoCols = {}, photoFolder = '';
    if (PHOTOS_PER_STOP > 0) {
      photoInfo = await get(`${list(PHOTOS)}?$select=ListItemEntityTypeFullName`);
      photoCols = await columns(PHOTOS);
      photoFolder = (await get(`${list(PHOTOS)}/RootFolder?$select=ServerRelativeUrl`)).ServerRelativeUrl;
      ['RunKey', 'StopKey', 'Item'].forEach(k => { if (!(k in photoCols)) out.push(`note: ${PHOTOS} has no ${k} column – the flow can't match photos without it`); });
    }

    // ---- the stops, planned up front (the app has them all before it sends anything)
    const stops = [];
    let t = 8 * 60; // first stop leaves CD at 08:00
    for (let i = 1; i <= Math.max(3, STOPS); i++) {
      const out_ = t, arrive = t + 20, start = arrive + 5;
      const dur = i === 2 ? 22 : 10;                        // stop 2: slow unload (>15 min)
      const temp = i === 1 ? -10 : -18;                     // stop 1: too warm (> -15 °C)
      const trade = i === 3;                                // stop 3: quantity mismatch
      stops.push({ no: i, key: crypto.randomUUID(), id: 0, temp, dur, trade, fields: {
        Title: `Test Customer ${i}`, StopOrder: i,
        TimeOut: hhmm(Math.floor(out_ / 60), out_ % 60), ArriveTime: hhmm(Math.floor(arrive / 60), arrive % 60),
        StartOpTime: hhmm(Math.floor(start / 60), start % 60), CompleteOpTime: hhmm(Math.floor((start + dur) / 60), (start + dur) % 60),
        Duration: dur, NoofCtns: 10 + i, NoofInvoices: PHOTOS_PER_STOP, TruckTemp: temp, Active: true,
        HSEQComments: `AUTOMATED TEST stop ${i}` + (i === 1 ? ' – warm truck' : i === 2 ? ' – slow unload' : trade ? ' – quantity short' : ''),
        TotalQty: 10 + i, ActualQty: trade ? 8 : 10 + i, TradeIssueReason: trade ? 'Test: 5 cartons short on delivery' : '',
      } });
      t = start + dur + 15;
    }
    const photoCount = stops.length * PHOTOS_PER_STOP;

    // ---- photo upload: file named like SaveFleetPhotos's, then its columns filled in
    const upload = async (s, slot, retake) => {
      const label = `photo stop ${s.no} · invoice ${slot}${retake ? ' (retake)' : ''}`;
      if (DRY_RUN) { out.push(label); return; }
      const blob = await invoiceJpeg(s.no, slot, retake);
      const name = `${TRUCK.replace(/ /g, '')}_${s.id}_Invoice_${stamp()}.jpg`;
      const r = await fetch(`${web}/_api/web/GetFolderByServerRelativeUrl('${enc(photoFolder)}')/Files/add(url='${enc(name)}',overwrite=true)`,
        { method: 'POST', body: blob, headers: { Accept: J, 'X-RequestDigest': digest } });
      if (!r.ok) { out.push(`  ${label} FAILED (${r.status}) ${(await r.text()).slice(0, 200)}`); return; }
      const item = await get(`${(await r.json()).d.__metadata.uri}/ListItemAllFields?$select=Id`);
      const m = await send(`${list(PHOTOS)}/items(${item.Id})`, only(photoCols, {
        __metadata: { type: photoInfo.ListItemEntityTypeFullName },
        Truck: TRUCK, PhotoType: 'Invoice', Item: `Stop ${s.no} · Invoice ${slot}`, RecordID: s.id,
        SourceList: STOPS_LIST, RunKey: runKey, StopKey: s.key,
      }), true);
      out.push(m.ok ? `${label}: ${name} (${Math.round(blob.size / 1024)} KB)` : `  ${label} uploaded but tagging FAILED (${m.status}) ${(await m.text()).slice(0, 200)}`);
    };
    const uploadAll = async () => {
      for (const s of stops) for (let k = 1; k <= PHOTOS_PER_STOP; k++) await upload(s, k, false);
      if (RETAKE && PHOTOS_PER_STOP > 0) { if (!DRY_RUN) await sleep(2); await upload(stops[0], 1, true); }
    };

    // ---- 1. photos first, as the app does with signal (stops not sent yet, so RecordID 0)
    if (PHOTOS_PER_STOP > 0 && PHOTOS_FIRST) await uploadAll();

    // ---- 2. the trip, once, already submitted (this starts the flow)
    const run = only(runCols, {
      __metadata: { type: runInfo.ListItemEntityTypeFullName },
      Title: TRUCK, RunDate: today.toISOString(), DateofDrive: today.toISOString(),
      DriverName: me, Partner: 'Test Partner', Area: 'Test Area', NoofInvoices: stops.length, StartMileage: 123000,
      ExpectedDeparture: '07:30', TimeReturned: hhmm(Math.floor(t / 60), t % 60), EndMileage: 123185,
      BalanceInvoice: 'TEST-INV-1', AnalogTemp_x002e_: -18, TemponPlugIn: -17, QtyonBalanceRecovery: 0, InvoiceBalanced: true,
      NoofStops: stops.length, NoofInvoicePhotos: photoCount, RunKey: runKey,
      Status: 'Open', ActiveYes_x002f_No: true,
    });
    if (runCols.Driver === 'Text') run.Driver = me;
    out.push(`trip: ${TRUCK}, Status Open, ${stops.length} stops, ${photoCount} invoice photos, RunKey ${runKey}`);
    let runId = 0;
    if (!DRY_RUN) {
      const r = await send(`${list(RUNS)}/items`, run);
      if (!r.ok) throw new Error(`Creating the trip failed (${r.status}): ${(await r.text()).slice(0, 300)}`);
      runId = (await r.json()).d.Id;
      out.push(`created trip ID ${runId} (the flow starts now)`);
    }

    // ---- 3. the stops
    for (const s of stops) {
      const stop = only(stopCols, Object.assign({ __metadata: { type: stopInfo.ListItemEntityTypeFullName },
        RunSheetId: runId, RunSheetID: runId }, s.fields));
      out.push(`stop ${s.no}: ${stop.Title}, ${s.temp} °C, ${s.dur} min` + (s.trade && 'ActualQty' in stop ? ', quantity mismatch' : ''));
      if (!DRY_RUN) {
        const r = await send(`${list(STOPS_LIST)}/items`, stop);
        if (r.ok) s.id = (await r.json()).d.Id;
        else out.push(`  FAILED (${r.status}) ${(await r.text()).slice(0, 200)}`);
      }
    }

    // ---- 4. photos late (the flow must wait for them)
    if (PHOTOS_PER_STOP > 0 && !PHOTOS_FIRST) {
      out.push(`waiting ${PHOTO_DELAY_SECONDS} s before the photos`);
      if (!DRY_RUN) { console.log(`Stops sent; uploading photos in ${PHOTO_DELAY_SECONDS} s. Keep this tab open.`); await sleep(PHOTO_DELAY_SECONDS); }
      await uploadAll();
    }
    // ---- 5. check what actually landed in the library
    if (!DRY_RUN && PHOTOS_PER_STOP > 0) {
      const expected = photoCount + (RETAKE ? 1 : 0);
      const found = (await get(`${list(PHOTOS)}/items?$filter=RunKey eq '${runKey}'&$select=Id&$top=500`)).results.length;
      out.push(`check: ${PHOTOS} has ${found} file(s) with this RunKey (expected ${expected})` +
        (found === expected ? '' : ' – PROBLEM: see the FAILED lines above'));
      out.push(`  to see them: open ${PHOTOS}, sort by Modified (newest first); names start with ${TRUCK.replace(/ /g, '')}_`);
    }
    out.push(`done. Expect the submission email after the flow's next check (every 2 min), with:`);
    out.push(`  - "Invoices: ${photoCount} photos, ${photoCount} attached" and ${photoCount} JPEGs attached (Stop1_Invoice1.jpg …)` +
      (RETAKE && PHOTOS_PER_STOP > 0 ? '; Stop1_Invoice1.jpg is the pink RETAKE page, the first copy must not be attached' : ''));
    out.push(`  - a link that opens ${PHOTOS} showing only this run's ${photoCount + (RETAKE && PHOTOS_PER_STOP > 0 ? 1 : 0)} photos` +
      (RETAKE && PHOTOS_PER_STOP > 0 ? ' (the library keeps the replaced copy too)' : ''));
  } catch (e) {
    out.push('STOPPED: ' + e.message);
  }
  console.log('=====\n' + out.join('\n') + '\n=====');
})();
