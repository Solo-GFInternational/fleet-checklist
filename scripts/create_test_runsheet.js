/*
  Creates a TEST run: one Run Sheets row and its stops in Run Sheet Details, the same way the app does
  (stops linked by the RunSheet lookup AND the RunSheetID number). Use it to test the run sheet flows.

  It behaves like a real driver, in two stages:
    1. Start the run (Status = In Progress) and add the stops. This must NOT send the submission email.
    2. If SUBMIT = true: fill in Return to CD and set Status = Open (submitted). This SHOULD send it.

  The stops include one of each case the emails flag:
    - a stop warmer than -15 °C           (⚠ in the submission email)
    - a stop that took over 15 min to unload (⚠ in the submission email)
    - a stop where Actual Quantity ≠ Total Quantity, with a reason (Trade Issue email),
      only if the TotalQty / ActualQty / TradeIssueReason columns exist.
  Run sheets have no photos in the app, so this script doesn't create any.

  Everything is marked as a test (comments "AUTOMATED TEST"; the truck is one of the 9 test registrations), so it's easy to delete.

  How to run:
    1. Open the Fleet Operations SharePoint site in Edge or Chrome.
    2. F12 → Console, paste this whole file, Enter. (Type "allow pasting" first if asked.)
    3. Leave DRY_RUN = true the first time: it prints what it would create.
    4. Set DRY_RUN = false and run again. Copy the text between the ===== lines if anything fails.
*/
(async () => {
  // ------------------------------------------------------------------ SETTINGS
  const DRY_RUN = false;
  const SUBMIT = true;            // false = leave the run In Progress (tests that NO email is sent)
  const STOPS = 5;                // how many stops (3 or more, so every test case is included)
  const SUBMIT_DELAY_SECONDS = 5; // pause between adding the stops and submitting
  const RUNS = 'Run Sheets';
  const STOPS_LIST = 'Run Sheet Details';
  // Test registrations from files/Fiji Number Plate QR Codes samples.docx; one is picked at random each run.
  const TRUCKS = ['FJ 101', 'CA 203', 'KI 123', 'LA 456', 'HX 789', 'GV 312', 'EF 645', 'JK 908', 'BN 274'];
  const TRUCK = TRUCKS[Math.floor(Math.random() * TRUCKS.length)];
  // ------------------------------------------------------------------

  const web = _spPageContextInfo.webAbsoluteUrl;
  const me = _spPageContextInfo.userDisplayName || 'Test Driver';
  const J = 'application/json;odata=verbose';
  const out = [DRY_RUN ? 'DRY RUN (nothing created)' : 'CREATING TEST RUN'];
  const list = t => `${web}/_api/web/lists/getbytitle('${encodeURIComponent(t.replace(/'/g, "''"))}')`;
  const get = async url => { const r = await fetch(url, { headers: { Accept: J } }); if (!r.ok) throw new Error(`${r.status} ${url}`); return (await r.json()).d; };
  const digest = (await (await fetch(`${web}/_api/contextinfo`, { method: 'POST', headers: { Accept: J } })).json())
    .d.GetContextWebInformation.FormDigestValue;
  const send = (url, body, merge) => fetch(url, { method: 'POST', body: JSON.stringify(body),
    headers: Object.assign({ Accept: J, 'Content-Type': J, 'X-RequestDigest': digest }, merge ? { 'X-HTTP-Method': 'MERGE', 'IF-MATCH': '*' } : {}) });
  const columns = async t => Object.fromEntries((await get(`${list(t)}/fields?$filter=Hidden eq false&$select=InternalName,TypeAsString`))
    .results.map(f => [f.InternalName, f.TypeAsString]));
  // keep only the values whose column exists (and, for Driver, is plain text)
  const only = (cols, obj) => Object.fromEntries(Object.entries(obj).filter(([k]) => k === '__metadata' || (k in cols) || (k.endsWith('Id') && (k.slice(0, -2) in cols))));
  const hhmm = (h, m) => `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  const today = new Date(); today.setHours(0, 0, 0, 0);

  try {
    const runInfo = await get(`${list(RUNS)}?$select=ListItemEntityTypeFullName`);
    const stopInfo = await get(`${list(STOPS_LIST)}?$select=ListItemEntityTypeFullName`);
    const runCols = await columns(RUNS);
    const stopCols = await columns(STOPS_LIST);
    if (!('RunSheetID' in stopCols)) out.push('note: Run Sheet Details has no RunSheetID column – the app and the submission email need it');

    // ---- 1. Start the run
    const run = only(runCols, {
      __metadata: { type: runInfo.ListItemEntityTypeFullName },
      Title: TRUCK, RunDate: today.toISOString(), DateofDrive: today.toISOString(),
      DriverName: me, Partner: 'Test Partner', Area: 'Test Area', NoofInvoices: STOPS, StartMileage: 123000,
      ExpectedDeparture: '07:30', ExpectedArrival: '16:00', Status: 'In Progress', ActiveYes_x002f_No: true,
    });
    if (runCols.Driver === 'Text') run.Driver = me;
    out.push(`run: ${TRUCK}, Status In Progress, ${Object.keys(run).length - 1} fields`);
    let runId = 0;
    if (!DRY_RUN) {
      const r = await send(`${list(RUNS)}/items`, run);
      if (!r.ok) throw new Error(`Creating the run failed (${r.status}): ${(await r.text()).slice(0, 300)}`);
      runId = (await r.json()).d.Id;
      out.push(`created run ID ${runId}`);
    }

    // ---- 2. Add the stops
    let t = 8 * 60; // first stop leaves CD at 08:00
    for (let i = 1; i <= Math.max(3, STOPS); i++) {
      const out_ = t, arrive = t + 20, start = arrive + 5;
      const dur = i === 2 ? 22 : 10;                        // stop 2: slow unload (>15 min)
      const temp = i === 1 ? -10 : -18;                     // stop 1: too warm (> -15 °C)
      const trade = i === 3;                                // stop 3: quantity mismatch
      const stop = only(stopCols, {
        __metadata: { type: stopInfo.ListItemEntityTypeFullName },
        Title: `Test Customer ${i}`, RunSheetId: runId, RunSheetID: runId, StopOrder: i,
        TimeOut: hhmm(Math.floor(out_ / 60), out_ % 60), ArriveTime: hhmm(Math.floor(arrive / 60), arrive % 60),
        StartOpTime: hhmm(Math.floor(start / 60), start % 60), CompleteOpTime: hhmm(Math.floor((start + dur) / 60), (start + dur) % 60),
        Duration: dur, NoofCtns: 10 + i, TruckTemp: temp, Active: true,
        HSEQComments: `AUTOMATED TEST stop ${i}` + (i === 1 ? ' – warm truck' : i === 2 ? ' – slow unload' : trade ? ' – quantity short' : ''),
        TotalQty: 10 + i, ActualQty: trade ? 8 : 10 + i, TradeIssueReason: trade ? 'Test: 5 cartons short on delivery' : '',
      });
      t = start + dur + 15;
      out.push(`stop ${i}: ${stop.Title}, ${temp} °C, ${dur} min` + (trade && 'ActualQty' in stop ? ', quantity mismatch' : ''));
      if (!DRY_RUN) {
        const r = await send(`${list(STOPS_LIST)}/items`, stop);
        if (!r.ok) out.push(`  FAILED (${r.status}) ${(await r.text()).slice(0, 200)}`);
      }
    }

    // ---- 3. Return to CD + submit
    if (SUBMIT) {
      const end = only(runCols, {
        __metadata: { type: runInfo.ListItemEntityTypeFullName },
        TimeReturned: hhmm(Math.floor(t / 60), t % 60), EndMileage: 123185, BalanceInvoice: 'TEST-INV-1',
        AnalogTemp_x002e_: -18, TemponPlugIn: -17, QtyonBalanceRecovery: 0, InvoiceBalanced: true, Status: 'Open',
      });
      out.push(`submit: time back ${end.TimeReturned}, end mileage ${end.EndMileage}, Status Open (submission email should follow)`);
      if (!DRY_RUN) {
        await new Promise(r => setTimeout(r, SUBMIT_DELAY_SECONDS * 1000));
        const r = await send(`${list(RUNS)}/items(${runId})`, end, true);
        out.push(r.ok ? 'submitted' : `submit FAILED (${r.status}) ${(await r.text()).slice(0, 200)}`);
      }
    } else {
      out.push('left In Progress (no submission email should arrive)');
    }
  } catch (e) {
    out.push('STOPPED: ' + e.message);
  }
  console.log('=====\n' + out.join('\n') + '\n=====');
})();
