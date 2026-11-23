# Fleet Checklist – Project Handover

Onboarding notes for a Claude Code session picking this project up cold. Read this first, then [PROJECT_HISTORY.md](PROJECT_HISTORY.md) for the day-by-day log.

- Written: 17 Nov 2026. Sources: `PROJECT_HISTORY.md` (last updated 2 Nov 2026), the build scripts, the generated files and file timestamps.
- The folder is **not a git repository**. Nothing is tracked, so treat every file as the only copy.
- Much of the real system lives in the cloud (Microsoft Forms, Power Automate, SharePoint, possibly Power Apps). The local files are specs, generators and helpers. **The live forms and lists have drifted from the generated files** (see [Drift](#6-current-state)).

---

## Contents

1. [Purpose and users](#1-purpose-and-users)
2. [The three forms](#2-the-three-forms)
3. [Tooling in this folder](#3-tooling-in-this-folder)
4. [SharePoint lists and Power Automate flows](#4-sharepoint-lists-and-power-automate-flows)
5. [Power Apps + SharePoint alternative](#5-power-apps--sharepoint-alternative)
6. [Current state](#6-current-state)
7. [Gotchas and quick reference](#7-gotchas-and-quick-reference)
8. [Setting up the 23–24 Nov 2026 release](#8-setting-up-the-2324-nov-2026-release)

---

## 1. Purpose and users

### What is being replaced

Three paper documents that the truck fleet fills in by hand every day:

| Paper document | Source | Filled in |
| --- | --- | --- |
| **Fleet Pre-Trip Checklist** | SOP DC/16.0 V007, Appendix III "Fleet Checklist" (PDF pages 10–11) | Before a vehicle is started, once per truck per day |
| **Fitness for Driving – Driver Declaration** | A separate scanned paper form ([21102026103050-0001.pdf](21102026103050-0001.pdf)) | By each driver at the start of a shift |
| **Vehicle Run Sheet** | SOP DC/16.0 V007, Appendix II (PDF page 9) | One per truck run, a row per delivery stop |

The SOP is [DC 16.0 DRIVER RESPONSIBILITIES & CUSTOMER SERVICE V007 16.07.2025.pdf](<DC 16.0 DRIVER RESPONSIBILITIES & CUSTOMER SERVICE V007 16.07.2025.pdf>) (11 pages: SOP body p1–6, appendix overview p7, Appendix I competency questionnaire p8, Appendix II run sheet p9, Appendix III fleet checklist p10–11).

### Target design

**Microsoft Forms** (drivers fill in on phones) → **Power Automate** (one flow per form, on each new response) → **SharePoint lists** on a "Fleet Operations" site, where the office reviews and actions them. A Power Apps front end over the same lists was planned as an alternative (section 5).

### Who uses what

| Role | Pre-Trip Checklist | Driver Declaration | Run Sheet |
| --- | --- | --- | --- |
| **Driver** | Fills in the checklist (Yes/No per item, comments per section, odometer, remarks) | Fills in details, answers 14 Yes/No declarations, comments, confirms | Fills in trip details, each stop, return-to-CD details |
| **Team Leader** | – | – | Verifies the run sheet (name in sign-off) |
| **Supervisor** | – | Signs off in the list (Supervisor Name / Date, office-only) and follows up any "No" | – |
| **Fleet Controller / Site Engineer / Manager** | Approves for delivery or sends for repairs (live form section, or office-only list columns) | – | – |
| **Project owner** | Owns forms, flows and lists; builds everything | | |

---

## 2. The three forms

All three are built as Word files laid out for **Forms Quick Import** (forms.office.com → New Form → Quick import → upload .docx → review → Import). Quick Import **cannot update an existing form**: to re-import, create a new form.

### Layout rules (user preferences, apply to all forms)

- Follow the paper documents' wording and item lists **exactly**.
- **Section titles are plain text**: no "Section 1", "Section 2"…
- **No stop numbers** in run sheet section or question titles in the generated file. (The live form later added them, see below.)
- Each check section: originally **one required "select all that apply" checkbox question plus a separate comments question**. Since 23 Oct 2026 the pre-trip checklist uses **one Yes/No question per item** plus a comments question per section (user's choice).
- **No answer lines** (`____`) under text questions (`answer_lines: False`).
- **Every section has a one-line description** right after its heading (stops Quick Import swallowing questions into the description).
- Date questions are named "Date", not "Date (date)".
- Dropped on purpose: sign/date lines (Forms records who and when), the SOP's own document "Reviewed By / Approved By" (document approvals, not per-run sign-off).
- When reporting changes back to the user, **show the resulting question list** so they can check it.

### 2.1 Fleet Pre-Trip Checklist

File: [Fleet Pre-Trip Checklist - MS Forms import.docx](<Fleet Pre-Trip Checklist - MS Forms import.docx>)

Current layout in `build_forms.py` (52 questions):

| Section | Questions |
| --- | --- |
| Engine and Transmission | 5 Yes/No items + "Engine and Transmission – comments" |
| Electrical System | 12 Yes/No items + comments |
| Body and Chassis | 6 Yes/No items + comments |
| Brakes and Tyres | 6 Yes/No items + comments |
| Safety Devices | 6 Yes/No items + comments |
| General | 5 Yes/No items + comments |
| Odometer and Remarks | Truck odometer reading before delivery (km); Remarks |
| Declaration by the Site Engineer / Fleet Controller | Approval for Delivery (Approved / Not Approved); Send for Repairs (Send / Don't Send); Manager / Warehouse Controller; Date of Declaration |

- 40 checklist items in total; each section description: "Answer Yes if the item has been checked and is in order. Note any defect in the comments."
- **No opening questions** (Site, Driver, Date, Truck, Fault were removed at the user's request). Driver and check date come from the Forms responder and submission time; truck identification is an open question.
- Page 2 guidance text of the paper form (points 1–6, "defects must be reported" paragraph) was given to the user to paste by hand into a section description.
- **Drift:** the .docx on disk (23 Oct 15:18, 51 questions) still ends with the older "Driver Declaration" section; `build_forms.py` (23 Oct 15:47) was updated afterwards to match the live form's Site Engineer section but the .docx was not regenerated.

Manual settings after import:

| Setting | Where |
| --- | --- |
| **Required** on every Yes/No item (and the Site Engineer questions, though the user may turn those off, see open questions) | Each question |
| (Older checkbox layout only) **Multiple answers** + **Required** on each checkbox question | Each section's checkbox question |
| Convert date questions to **Date** type | Any date that imported as text |
| **Restrictions → Number** on the odometer | Odometer question |

### 2.2 Fitness for Driving – Driver Declaration

File: [Fitness for Driving Driver Declaration - MS Forms import.docx](<Fitness for Driving Driver Declaration - MS Forms import.docx>) (19 questions, rebuilt 23 Oct 2026, re-saved through Word).

| Section | Questions |
| --- | --- |
| Driver Details | Driver full name; Employee number; Date |
| Declarations ("I hereby declare that I:") | 14 required Yes/No declarations (licence, rest ≥ 9 h, not impaired, testing, passengers, legislation, false declaration, etc.) |
| Comments | Comments (details of any "No") |
| Driver Sign-off | "I confirm that the declarations above are true and correct." → I agree |

- Supervisor section removed from the form; supervisor fills **Supervisor Name / Supervisor Date** in the list.
- Status: imported, flow built, list populating (see section 6).

### 2.3 Vehicle Run Sheet

File: [Vehicle Run Sheet - MS Forms import.docx](<Vehicle Run Sheet - MS Forms import.docx>) (197 questions). Built from **SOP page 9 (Appendix II)**. Form title "Driver Responsibilities and Customer Service".

| Section | Questions | Notes |
| --- | --- | --- |
| Trip Details | 1–9: Date, Truck #, Driver, Partner, Area, # Of Invoices, START Mileage, Expected Departure Time (CD), Expected Time of Arrival (CD) | |
| Delivery Stop ×18 | 10 per stop: Time Out, Destination, # of Ctns, Arrive Time, Truck Temp (°C), Start Op Time, Complete Op Time, Duration (minutes), HSEQ Observations/Issues/Comments, "Do you have another delivery stop?" (Yes/No) | 18 rows on the paper sheet; last stop has no "another stop?" |
| Return to CD | Time truck returned, END Mileage, Balance invoice, Analog Temp. (°C), Temp. on Plug in (°C), Qty on Balance Delivery, Invoice Balanced with Cashier (Yes/No) | END Mileage moved here from the header (known only at the end) |
| Sign-off | Truck Driver's Name; Verified By: Team Leader Name | |

- Times are **text** ("hh:mm, 24-hour"); Forms has no time type.
- **200-question limit:** Forms allows 200 questions per form. 197 used → only 3 spare. To add fields, drop a stop or a field (e.g. Duration can be computed from start/complete times).

Manual settings after import:

| Setting | Detail |
| --- | --- |
| **Branching** | On each "Do you have another delivery stop?": Yes → next section, No → Return to CD |
| **Restrictions → Number** | Invoices, mileages, # of Ctns, temperatures, Duration, Qty (required, or the flow's number conversion fails) |
| **Required** | The six numeric header/return fields were made Required to match Required list columns |

**Live form differences (made directly in Forms, not in the .docx):**
- **17** stop sections (titles end "- 1" … "- 17"), not 18.
- The 9 flow-read stop questions end in "(S1)" … "(S17)" so Power Automate's dynamic-content picker can tell them apart ("another stop?" not renamed). This relaxes the "no stop numbers" rule.
- Sign-off gained **Date of Drive** and **Date Verified**, plus a **Review and Approval** section (Reviewed By, Date Reviewed, Approved By, Date Approved). No list columns for these yet.
- END Mileage was not seen in Return to CD on 22 Oct; check where it is.

---

## 3. Tooling in this folder

### File map

| File | Date | What it is |
| --- | --- | --- |
| [PROJECT_HISTORY.md](PROJECT_HISTORY.md) | 2 Nov | Running history / decision log |
| [build_forms.py](build_forms.py) | 23 Oct | Generates the Forms Quick Import .docx files |
| [build_lists.py](build_lists.py) | 23 Oct | Generates Excel starter files for creating SharePoint lists |
| [email-templates/](email-templates/) | 23 Oct | HTML email bodies for Power Automate alerts |
| [Fleet Pre-Trip Checklist - MS Forms import.docx](<Fleet Pre-Trip Checklist - MS Forms import.docx>) | 23 Oct | Forms import file (stale vs script, see 2.1) |
| [Fitness for Driving Driver Declaration - MS Forms import.docx](<Fitness for Driving Driver Declaration - MS Forms import.docx>) | 23 Oct | Forms import file |
| [Vehicle Run Sheet - MS Forms import.docx](<Vehicle Run Sheet - MS Forms import.docx>) | 20 Oct | Forms import file (18 stops; live form has 17) |
| [Fleet Pre-Trip Checks.xlsx](<Fleet Pre-Trip Checks.xlsx>) | 23 Oct | List template, 57 columns (generated, sample row only) |
| [Driver Declarations.xlsx](<Driver Declarations.xlsx>) | 23 Oct | List template, 21 columns (generated, sample row only) |
| [Vehicle Run Sheets - SharePoint list.xlsx](<Vehicle Run Sheets - SharePoint list.xlsx>) | 21 Oct | List template, 18 columns |
| [Vehicle Run Sheet Stops - SharePoint list.xlsx](<Vehicle Run Sheet Stops - SharePoint list.xlsx>) | 21 Oct | List template, 11 columns |
| [Forms Test Data Generator.xlsx](<Forms Test Data Generator.xlsx>) | 27 Oct | Formula-driven generator of random dummy test responses via pre-filled links |
| [DC 16.0 … V007 16.07.2025.pdf](<DC 16.0 DRIVER RESPONSIBILITIES & CUSTOMER SERVICE V007 16.07.2025.pdf>) | – | Source SOP |
| [21102026103050-0001.pdf](21102026103050-0001.pdf) | 21 Oct | Scan of the paper Fitness for Driving declaration (image only, no text layer) |

### 3.1 `build_forms.py`

- **Purpose:** writes Word XML directly (stdlib `zipfile`) into a minimal .docx that Quick Import understands: Title style = form title, Heading 1 = section, a description paragraph, numbered bold question lines `N. text`, lettered indented options `A. Yes`.
- **Usage:** `python build_forms.py <out_dir> [fleet|run|decl]` (no second argument = all three). Prints `<path>: N questions`.
- **Content lives in the script:** `CHECKS` (pre-trip items), `fleet`, `run` (`stop()` + `STOPS = 18`), `DECLARATIONS`, `declaration`. Each form dict has `file`, `title`, `intro`, `answer_lines`, `sections` = list of `(name, description, [(question, options|None)])`.
- **Dependencies:** Python 3 standard library only.
- **Post-step (manual):** re-save the output through Word so the importer gets a standard Word package (run sheet since 20 Oct, declaration since 23 Oct). Build into a temp folder, then in PowerShell:
  ```powershell
  $w = New-Object -ComObject Word.Application
  $d = $w.Documents.Open("<temp>\file.docx"); $d.SaveAs2("<project>\file.docx", 16); $d.Close(); $w.Quit()
  ```
- **It overwrites files in `<out_dir>`.** Build into a scratch folder first if you only want to inspect.

### 3.2 `build_lists.py`

- **Purpose:** writes .xlsx workbooks (stdlib `zipfile`) for SharePoint → + New → List → **From Excel**. Each has:
  - Sheet **List**: an Excel table of the column headers plus **one sample row** (dummy values like "Sample Driver") so SharePoint can guess types. Delete that row after import.
  - Sheet **Column guide**: internal name, label to show, SharePoint type to pick, choices.
- **Usage:** `python build_lists.py <out_dir> ["List name" ...]`, e.g. `python build_lists.py . "Pre-Trip Checks" "Driver Declarations"`. List names: `Pre-Trip Checks`, `Run Sheets`, `Run Sheet Details`, `Driver Declarations`.
- **Outputs:** `Fleet Pre-Trip Checks.xlsx`, `Vehicle Run Sheets - SharePoint list.xlsx`, `Vehicle Run Sheet Stops - SharePoint list.xlsx`, `Driver Declarations.xlsx`. (PROJECT_HISTORY calls two of these "… - SharePoint list.xlsx"; the script's actual names are the short ones.)
- **Header naming:** short, no spaces (`TruckNo`, `D01Licence`) because SharePoint fixes the internal name at creation and Power Apps uses it. Exception: lists in `SPACED` (`Pre-Trip Checks`, `Driver Declarations`) get spaces inserted ("Check Date" → internal `Check_x0020_Date`) at the user's request.
- **Dependencies:** Python 3 standard library only.

### 3.3 `email-templates/`

Inline-styled HTML bodies for Office 365 Outlook "Send an email (V2)" (paste into the body in code view, replace placeholders with dynamic content).

| File | Use | Placeholders |
| --- | --- | --- |
| [declaration-no-alert.html](email-templates/declaration-no-alert.html) | Compact red alert: a driver answered No to a declaration | `DRIVER`, `EMPNO`, `DATE`, `COMMENTS`, `LIST_LINK` |
| [declaration-no-alert-detailed.html](email-templates/declaration-no-alert-detailed.html) | Same, plus all 14 declarations with Yes/No labels | above + `D01_ANSWER`/`D01_COLOUR` … `D14_…` |
| [flow-failure.html](email-templates/flow-failure.html) | A flow failed, response may be missing | `FLOW_NAME`, `FAIL_TIME`, `RESPONSE_ID`, `RUN_LINK` |
| [preview.html](email-templates/preview.html) | Open in a browser to see all three (Option A, Option B, failure) | – |

Email alerts are **on hold** (see gotchas): no Send As on the shared mailbox.

### 3.4 Test data

`Forms Test Data Generator.xlsx`: sheet **Setup** (paste a Forms pre-filled link), sheet **Tests** (20 random dummy responses as pre-filled links). Long pre-filled links (> ~2,250 chars) fail through organisation sign-in (AADSTS90015): blank long answers or use a short link.

---

## 4. SharePoint lists and Power Automate flows

### 4.1 Lists (site "Fleet Operations")

| List | Row = | Key columns | Notes |
| --- | --- | --- | --- |
| **Pre-Trip Checks** (template) | one checklist | Check Date, Truck No, Driver Name, Site, 40 Yes/No Choice columns (prefixed Eng/Elec/Body/Brk/Safe/Gen + number), 6 comments (multi-line), Odometer, Remarks, Approval For Delivery, Send For Repairs, Manager Name, Date Of Declaration, Response ID | 57 columns |
| **Fleet Checklist** (live, Power Apps track) | one checklist | The pre-trip items by section (Engine, Electrical, Body, Brakes, Safety, General), a comments column per section, Odometer | Being set up for the Power Apps form; check its column settings before changing it |
| **Driver Declarations** | one declaration | Decl Date, Driver Name, Employee No, D01…D14 (Yes/No), Comments, Driver Confirmed, Supervisor Name / Supervisor Date (office use) | Live and populating |
| **Run Sheets** | one trip | Title shown as "Truck #", Run Date, Driver, Partner, Area, No of Invoices, Start/End Mileage, Expected Departure/Arrival, Time Returned, Balance Invoice, Analog Temp., Temp on Plug In, Qty on Balance Delivery, Invoice Balanced (Yes/No), Driver Name, Team Leader, Response ID, Active (Yes/No) | Six Number columns Required. List may still be titled "Fleet Operations"; a "Qty on Balance Recovery" typo was to be renamed |
| **Run Sheet Details** (stops) | one stop | Title shown as "Destination", **Run Sheet** (Lookup → Run Sheets, showing ID), Time Out, No of Ctns, Arrive Time, Truck Temp, Start/Complete Op Time, Duration, HSEQ Comments, Active | Replaced "Run Sheet Stops" on 2 Nov after its permissions broke. **No Stop Order** set: sort by ID within a trip |
| Defect Photos (library) | photo | – | Only if photo upload is added |

Design rules:
- **Times** are Single line of text (date-time with dropdowns was offered, not chosen).
- **Internal names are permanent.** Create columns with short no-space names, then change the display name.
- **Indexing / volume:** about 15,000 responses a year for 20 trucks. Index **Date** and **Truck** columns and use filtered views ("Last 7 days", "Open defects") to stay under the 5,000-item view threshold. Add indexes before lists grow.
- **Office-only status columns** (drivers never see them): Status (Open / Approved / Sent for repairs / Fixed), Actioned By, Date Fixed; Supervisor Name/Date on declarations. Template Run Sheets also has Status (In progress / Submitted).
- **Deactivate, don't delete:** an `Active` Yes/No column is used (owner's convention). Created / Created By / Modified / Modified By are SharePoint built-ins.
- Pre-trip ticked items were once planned as one multi-line text column per section ("; "-joined) for flexibility; superseded by one Choice column per item.

### 4.2 Flows (one per form, "When a new response is submitted")

| Flow | Steps | Status |
| --- | --- | --- |
| **Driver Declaration → SharePoint** | Trigger → Get response details → Create item (Driver Declarations) → (Condition: any declaration = "No" → alert) | Working; alert condition was being added 23 Oct; email part on hold |
| **Run Sheet → SharePoint** | Part A: Trigger → Get response details → Create item (Run Sheets). Part B: one block per stop: Condition `empty(Destination (Sn))` is equal to `false` → Create item (Run Sheet Details) with `Run Sheet ID = outputs('Create_item')?['body/ID']` | **Done** (confirmed 26 Oct; rebuilt 2 Nov for Run Sheet Details) |
| **Pre-Trip → SharePoint** | Trigger → Get response details → Create item (Pre-Trip Checks) | All fields mapped; **full test not run** |

### 4.3 Power Apps flow: SaveFleetPhoto

Called from `scrPreTrip` (`frmPreTrip.OnSuccess`) once per photo in `colPhotos` (odometer, 18 accessory photos, any defect photos), after the checklist row is saved:

`'SaveFleetPhoto'.Run(Truck, PhotoType, Item, RecordID, SourceList, {file: {name: "photo.jpg", contentBytes: <image>}})`

| # | Trigger input (When Power Apps calls a flow, V2) | Type | Example |
| --- | --- | --- | --- |
| 1 | Truck | Text | `FT 1234` |
| 2 | PhotoType | Text | `Odometer`, `Accessory`, `Defect` |
| 3 | Item | Text | `Spare Tyre Availability` (accessory column display name) or the driver's description |
| 4 | RecordID | Number | ID of the Fleet Checklist row |
| 5 | SourceList | Text | `Fleet Checklist` |
| 6 | file | File | the photo |
| 7 | RunKey | Text, optional | run sheet `LocalKey` (invoice photos only, added 23 Nov 2026) |
| 8 | StopKey | Text, optional | stop `LocalKey` (invoice photos only, added 23 Nov 2026) |

Inputs 7–8 need two text columns, `RunKey` and `StopKey`, on the library (`scripts/create_runsheet_v2_columns.js`), and *Update file properties* must fill them. Optional inputs can be left out, so scrPreTrip's six-argument call keeps working. After adding them, remove and re-add the flow in the app. The run sheet uploads invoice photos with PhotoType `Invoice`, Item `Stop N · Invoice k`, RecordID = the stop ID (0 if the stop isn't sent yet) and SourceList `Run Sheet Details`.

Setup (not documented before 20 Nov 2026; confirm whether the live flow matches):
- **Library:** a document library on Fleet Operations (planned as "Defect Photos"; "Fleet Photos" fits better now) with columns `Truck` (text), `PhotoType` (text), `Item` (text), `RecordID` (number), `SourceList` (text), internal names typed first.
- **Flow:** instant cloud flow named exactly **SaveFleetPhoto**, trigger *When Power Apps calls a flow (V2)* with the six inputs above **in that order** → SharePoint **Create file** (folder = the library; name e.g. `concat(replace(triggerBody()['text'],' ',''),'_',triggerBody()['number'],'_',triggerBody()['text_1'],'_',formatDateTime(utcNow(),'yyyyMMddHHmmssfff'),'.jpg')`; content = the `file` input's content) → SharePoint **Update file properties** (ItemId from Create file) filling the five columns.
- **In the app:** Studio → Power Automate pane → *Add flow* → SaveFleetPhoto. Re-add it whenever the trigger inputs change.
- Runs with the flow owner's SharePoint connection, so drivers don't need access to the library. Add a co-owner, as for the other flows.
- A checklist with all photos makes ~19 calls; on failure the app shows "Checklist saved, but the photos did not upload" and the checklist itself is kept.

"Loop" for stops: Forms returns one flat response, so there is no array to iterate. Each stop is a **copied block** keyed to its own question IDs (S1…S17). Stops 1–5 were built by hand; 6–17 were generated from a copy of Stop 5's action JSON with question IDs swapped (IDs from the form's question list via browser DevTools → Network), then added with "Paste an action". Any temp files used for that held site/list/connection details and were deleted. Don't keep them in this folder.

Expressions that work:
- Numbers: `if(isFloat(x), float(x), null)` (plain `float()` fails on non-numeric text).
- Yes/No to boolean: `equals(<answer>,'Yes')`.
- Required list columns appear at the top of the Create item card.

Alerts:
- Planned: Fleet Controller alert on defect comments / "Not OK", supervisor alert on any declaration "No", owner alert on flow failure (templates in 3.4).
- Use a **Teams Flow bot post** if email stays blocked.
- Suggested: move manager approval out of the driver's form into a Power Automate **Approval** to the Fleet Controller.

### 4.4 Power Apps flow: SyncAppUser (built and tested 23 Nov 2026)

Called from `scrUsers` (Add person, Save role, Remove access / Give access back). It's the only thing that writes to the App Users list or changes group membership, and it runs under the flow owner's connections, so Admins don't need SharePoint rights of their own. Adding someone to a SharePoint group through the REST API sends **no email**.

`SyncAppUser.Run(Email, Name, Role, Active)` → returns `ok` (Yes/No) and `message` (text).

| # | Trigger input (When Power Apps calls a flow, V2) | Type | Example |
| --- | --- | --- | --- |
| 1 | Email | Email (`triggerBody()['email']`) | the person's sign-in address, lower case |
| 2 | Name | Text (`['text']`) | `Krish Kumar` |
| 3 | Role | Text (`['text_1']`) | `Driver`, `Reviewer`, `Admin` |
| 4 | Active | Yes/No (`['boolean']`) | `true` = has access, `false` = remove access |

Steps:
1. **Caller check.** Get items on App Users, filter `UserEmail eq '@{toLower(triggerOutputs()?['headers']?['x-ms-user-email'])}' and AppRole eq 'Admin' and ActiveYN eq 1`, top 1. If none, respond `ok = false`, "Only admins can manage users", and Terminate. This check is what stops a non-admin from calling the flow directly.
2. **Upsert the App Users row.** Get items filter `UserEmail eq '<email>'`, top 1. If found, Update item (Title = Name, AppRole = Role, ActiveYN = Active); otherwise Create item.
3. **Ensure user.** *Send an HTTP request to SharePoint*, POST `_api/web/ensureuser`, headers `Accept` and `Content-Type` = `application/json;odata=verbose`, body `{"logonName":"<email>"}`. Keep `body('Ensure_user')?['d']?['Id']` and `?['LoginName']`.
4. **Remove from both groups.** Two HTTP POSTs: `_api/web/sitegroups/getbyname('Fleet App Drivers')/users/removebyid(<Id>)`, then the same for `Fleet App Reviewers`. Set each one's *Configure run after* to continue on failure (it fails when the person wasn't in that group).
5. **If Active:** HTTP POST `_api/web/sitegroups/getbyname('<group>')/users`, body `{"__metadata":{"type":"SP.User"},"LoginName":"<LoginName>"}`. Use group `Fleet App Drivers` for Driver and `Fleet App Reviewers` for Reviewer/Admin.
6. **Optional: share the app.** *Power Apps for Makers → Edit App Role Assignment* (the flow owner must own the app), role CanView. Not tested here: check on the first run whether an invitation email arrives. Otherwise share the app by hand or with a security group from IT.
7. **Respond to a PowerApp or flow:** `ok = true`, `message` = for example "Added to Fleet App Drivers".

Removing access keeps the person's past records (Created By doesn't change) and keeps the App Users row with Active = No.

Setup: run `scripts/setup_app_permissions.js` (groups, permission levels, list permissions) once before the flow is used. In the app: Power Automate pane → Add flow → SyncAppUser, and Add data → **Office 365 Users** (the people search on scrUsers).

### 4.5 Power Apps flow: RunSheetSubmitted (designed 23 Nov 2026, not built yet)

Called by `btnRunSync` on scrRunSheet once the trip and every stop are in SharePoint and no invoice photo is still waiting to upload. The app calls it directly because a SharePoint trigger would fire before the stops exist. If the call fails, the app shows a warning and still clears the run.

`'RunSheetSubmitted'.Run(RunSheetID, RunKey)` → returns `ok` (Yes/No) and `message` (text). Both inputs are text.

Steps:
1. Get the Run Sheets item. If `SubmissionEmailSent` is already true, respond `ok = true` and stop, so the email is never sent twice.
2. Get items from Run Sheet Details with `RunSheetID eq <id>`, ordered by StopOrder.
3. Get files from the Fleet Photos library with `RunKey eq '<RunKey>'`, ordered by Created. Keep the latest file per StopKey + slot. The slot is the "Invoice k" part of `Item`, and a retake uploads a second file.
4. Get each file's content and build one HTML page: a summary table (truck, driver, date, area, stops, cartons, flagged stops), then one `<div style="page-break-before:always"><img src="data:image/jpeg;base64,…" style="width:100%"></div>` per invoice.
5. OneDrive for Business: **Create file** (.html), then **Convert file** to PDF. This is a standard connector, so no premium licence is needed.
6. Outlook **Send an email (V2)** with the body from [email-templates/run-sheet-submitted.html](email-templates/run-sheet-submitted.html) and the PDF attached. It sends from the flow owner's mailbox until IT grants Send As on the shared mailbox; a Teams post with the PDF is the fallback.
7. Delete the temporary OneDrive files.
8. Update the Run Sheets item: `SubmissionEmailSent = true`.
9. Respond to Power Apps with `ok` and `message`.

In the app: Power Automate pane → Add flow → RunSheetSubmitted.

### 4.6 Licensing, ownership, service account

- **Drivers ideally have Microsoft 365 accounts** (Frontline F1/F3 are cheaper): Forms then records who submitted and when, and file upload (photos) works only on organisation-only forms. Confirm with IT.
- Forms + standard SharePoint/Outlook/Teams connectors run on standard M365 licences. Anything premium (Dataverse, premium connectors, Power Apps offline-first on Dataverse) needs Power Apps/Automate premium licences: check before designing for it.
- **Ownership:** create forms under a Microsoft 365 group / Team (e.g. "Fleet Operations"), not a personal account, so the organisation owns them.
- **Flows:** add a **co-owner** (still to do); ideally run connections under a dedicated service account so flows survive staff changes.
- **Email:** sending as a shared mailbox needs **Send As** granted by IT.
- Rough effort: lists 1–2 h, importing/configuring forms ~1 h, each flow ~½ day, QR codes per truck ~1 h, pilot 1–2 trucks for a week.

---

## 5. Power Apps + SharePoint alternative

On 21 Oct 2026 the user chose **Power Apps + SharePoint lists** over Forms + Power Automate, mainly for offline use and control over truck/driver/date. Work then continued on Forms + flows (working by 26 Oct), and in mid-November Power Apps work resumed on the **Fleet Checklist** list. **Both tracks exist; confirm with the user which is the go-live path.**

| Phase | Content | State |
| --- | --- | --- |
| 0. Spec | The Forms .docx files are the question spec | Done |
| 1. Lists | Create lists from the `build_lists.py` templates (short internal names, stops in their own list linked by run-sheet ID + stop order) | Run sheet + declaration lists exist; Fleet Checklist list being set up |
| 2. Canvas apps | One screen/app per form over the lists; app fills Driver (signed-in user), Date (today), Truck (dropdown or QR code); run sheet adds any number of stops | In progress for pre-trip checklist (status unknown) |
| 3. Offline | Canvas app offline mode (SaveData/LoadData queue, or Dataverse offline if licensed) | Not started; Forms cannot submit offline |
| 4. Pilot | 1–2 trucks for a week, then roll out | Not started |
| Extras | Defect photo upload, Power BI dashboard | Ideas |

Offline completion estimates given to the user (22 Oct): run sheet online-only ~60%, both forms with pilot ~45%, true offline ~35%.

### Power Apps run sheet (18 Nov 2026)

- One screen, [screens/scrRunSheet.txt](screens/scrRunSheet.txt), with three tabs: **Trip** (creates/updates the parent row in `Run Sheets`) → **Stops** (each stop saved straight to `Run Sheet Details`, linked by the `RunSheet` lookup, numbered by `StopOrder`; no limit, runs are typically ~70 stops) → **Return to CD** (footer fields, then submit).
- Column names come from the live lists (dumped 18 Nov with [scripts/list_columns.js](scripts/list_columns.js)), not the Excel templates in `files/`. Odd internal names: `NoofInvoices`, `AnalogTemp_x002e_`, `TemponPlugIn`, `QtyonBalanceRecovery` (shown as "Qty on Balance Delivery"), `ActiveYes_x002f_No`, `NoofCtns`. Truck number is `Title` on Run Sheets; destination is `Title` on Run Sheet Details. `InvoiceBalanced` is Yes/No (Boolean).
- Status: the app writes **Open** on submit (same as Forms submissions: waiting for the Team Leader), and the office sets **Closed**. Since 23 Nov 2026 nothing is written before submit (drivers are add-only), so **In Progress** is no longer used; it stays in the Status choices for older rows.
- End Mileage, Analog Temp., Temp on Plug In and Qty on Balance Delivery must **not** be Required in SharePoint, or the run can't be saved at the start. The app enforces them on the Return to CD tab instead.
- Home's Run sheet button reopens the run saved on the phone. It no longer reopens an "In Progress" run from SharePoint, because finishing it would mean editing that row. Finish or clear any run started on the old version before switching.
- Team Leader verification (`TeamLeader`, `DateVerified`, review/approval columns) is still to be built on a review screen.


### Power Apps driver declaration (19 Nov 2026)

- [screens/scrDecl.txt](screens/scrDecl.txt) writes to `Driver Declarations`. That list was created from Excel, so its internal names are `field_N`: `Title` = driver name, `field_0` Decl Date (date-time), `field_2` Employee No, `field_3`…`field_16` = D01…D14 (single line of text, "Yes"/"No"), `field_17` Comments (single line of text, 255 max), `field_19`/`field_20` Supervisor Name/Date (office only).
- Wording is from [files/Fitness for Driving Driver Declaration Form.pdf](<files/Fitness for Driving Driver Declaration Form.pdf>). Each statement is a checkbox (ticked = "Yes", unticked = "No"); any unticked statement makes Comments required and warns the driver to tell their Supervisor. The 40 checklist items on scrPreTrip are checkboxes too (19 Nov 2026); Approval for Delivery and Send for Repairs stay drop-downs. Employee No is pre-filled from the driver's last declaration.


### Power Apps review and sign-off (19 Nov 2026)

- [screens/scrReview.txt](screens/scrReview.txt): three tabs, each with a Waiting / All filter.
  - **Checklists**: `Fleet Checklist` rows without Approval for Delivery (`field_52`) are "waiting". Tapping one opens scrPreTrip in review mode (unchanged).
  - **Run sheets**: `Run Sheets` with Status "Open" are waiting. The detail view shows the run and its stops from `Run Sheet Details` (red = above -15 °C or unloading over 15 min). **Verify run sheet** sets `TeamLeader` = reviewer, `DateVerified` = now, Status "Closed".
  - **Declarations**: `Driver Declarations` without Supervisor Name (`field_19`) are waiting; any "No" answer shows in red. **Sign off** sets `field_19` = reviewer, `field_20` = now.
- Anyone who opens the screen can sign off until roles/permissions are added. Reviewed By / Approved By on Run Sheets are not used yet.

### Meeting changes (23 Nov 2026, from the review with Pawan's team)

**Fleet Checklist.** The screen is now generated, not hand-edited:
- [scripts/checklist_items.json](scripts/checklist_items.json) is the single source for item order, section, wording, optional instruction line (empty for now), photo rule, who answers it, weekly flag and truck-type rule.
- `py -3 -I scripts/build_pretrip_screen.py screens` rebuilds [screens/scrPreTrip.txt](screens/scrPreTrip.txt). **Change the JSON and regenerate; don't edit scrPreTrip.txt by hand.**
- The proposed wording for Pawan's approval is in [files/Fleet Checklist - item wording for approval.md](<files/Fleet Checklist - item wording for approval.md>). The screen shows each column's SharePoint display name, so approved wording is applied by renaming columns (`scripts/create_checklist_v2_columns.js`, rename mode), with no app change.
- Sections in order: Truck and driver, Licence and Odometer, Cabin (ends with the Net/Gross weight photo), Electrical, Tyres, Leaks and Fluid Levels, Body and Chassis, Safety, General, Accessory Checks, Accident Imagery, Truck Profiles (Front, Rear, Left, Right photos), Other comments.
- Every item has a Yes and a No box, with nothing ticked at the start. Each item is worded as what the driver should see, 7 words at most (for example "No new dents or cracks"), so No always means a problem. The comment box (inside the item's card) opens on No (Accident damage also needs photos on No). Each No is saved as a row in the **GF Fleet Checklist Defects** list after the checklist is saved, not in a column. Submit waits until every item is answered, every comment is filled, Site and odometer are filled, and every required photo is taken.
- New columns: `LicenceValid`, `CabGlassDriver`, `CabGlassPassenger`, `CabTilt`, `AccidentDamage` (`scripts/create_checklist_v2_columns.js`). The earlier `…Cmt` comment columns were dropped for the Defects list; if any were already created they are unused and can be deleted.
- Hidden but kept in SharePoint: Money Box (`field_48`) and the per-section comment columns.
- The truck number is locked to the truck chosen on Home, and Site is required.
- **Weekly reviewer-only items:** Cabin tilting (`CabTilt`) and Underneath greasing (`field_44`). Drivers don't see them. When a reviewer opens a checklist, the app looks for a signed-off checklist for the same truck in the same Monday–Sunday week with that item = Yes. If one exists, it shows "… inspection conducted on {date} by {name}" (from that record's `field_55` / `field_54`) instead of the boxes.
- **Photos:** a retake replaces the earlier photo. There is one photo per tyre (count from the Trucks list, 6 if the truck isn't listed), four profile photos and any number of accident photos.

**GF Fleet Checklist Defects list** (`scripts/create_checklist_defects.js`):
- One row per checklist item answered No: Title = item wording, `ChecklistID` (the Fleet Checklist row's ID, indexed), `Truck` (indexed), `ItemField` (the item's internal column name), `Comment`. No status or audit columns (user's decision); SharePoint's Created / Created By record when and by whom.
- Drivers add only (Fleet App Driver level, own items); Reviewers view, add and edit everyone's (Fleet App Reviewer).
- The driver's rows are written in `frmPreTrip.OnSuccess` after the checklist row exists (two-step save). Any row or photo that fails is queued on the phone and resent from Home (see Checklist improvements below). The weekly reviewer items add their row from Save sign-off.
- When a reviewer opens a checklist, `OnVisible` loads its rows into `colCheckDefects` and each comment box shows its row's comment, view-only.

**GF Fleet Trucks list** (`scripts/create_trucks_list.js`):
- Columns: Title = truck number ("FJ 101" format), `TruckType` (Ambient/Frozen), `NoOfTyres`, `ActiveYN`, due dates `COFExpiry`, `BlowerServiceDue`, `TruckServiceDue` (date only). Rerun the script on the existing list to add the new columns; the optional CSV can carry `COF,BlowerService,TruckService` dates (new trucks only).
- Drivers have Read. Fleet App Reviewers have Fleet App Reviewer (edit items) so the office keeps the due dates current; the script removes their old Read grant.
- scrPreTrip looks up the truck into `varTruckInfo`. It sets the tyre-photo count and hides items whose truck type doesn't match. Today only Blower service due and Plug wire are Frozen-only, as placeholders until Krish confirms. Krish provides the full truck table.

**Run sheet:**
- Trip tab: "Actual times" with Actual departure time only (still stored in `ExpectedDeparture`). `ExpectedArrival` is no longer filled; Time returned is the arrival.
- Every time field is two boxes, HH : MM, joined into "HH:MM".
- Stop order: Arrive time first, "Time left the premises" (`TimeOut`) last.
- New per-stop **No. of invoices** (`NoofInvoices` on Run Sheet Details), with one in-app camera photo per invoice. There's no gallery access, so drivers can't upload old pictures.
- The truck number is locked when it came from Home.
- Invoice photos are queued on the phone and uploaded on every sync (see CLAUDE.md, Offline). The **RunSheetSubmitted** flow (4.5) emails a PDF of all of a run's invoices.

**Checklist improvements (23 Nov 2026, approved by the user):**
- **Due dates from the truck.** COF expiry, Blower service due and Truck service due (`"truckDate"` in the JSON) show the truck's date read-only with **Expired** (red), **Due within 30 days** (amber) or **OK** (teal); no date picker or photo, and the date is saved on the checklist as a snapshot. If the truck isn't listed or the date is blank, the old date picker + required photo come back.
- **Draft on the phone.** Answers, comments, dates and header fields are saved on the phone as the driver goes ("fcCheckDraft", photos "fcCheckPhotos"). If the app closes, Home shows "You have an unfinished checklist for <truck> started <time>" with **Carry on** and **Discard** (tap twice). Start fleet checklist stays disabled until the draft is finished or discarded. Defect rows and photos that fail after the checklist row is saved are kept on the phone ("fcCheckRetry", "fcCheckRetryPhotos") and resent from Home when there's signal, which closes the two-step-save gap.
- **One section per page.** 12 pages for drivers (Truck and driver + Licence and Odometer on page 1), 11 when reviewing (no Truck Profiles page). Footer: progress label "Section 3 of 12 · Tyres" with a thin bar, **Back** / **Next**, "N still to do" for the page (Next is never blocked), and on the last page Submit plus **Go to it**, which jumps to the page of the first missing item. Sign-off cards are on the last page.

**Daily review:**
- List **GF Fleet Daily Reviews** (`scripts/create_daily_reviews.js`): Title = driver, `DriverEmail`, `ReviewDate`, `Stars` 1–5, `Comment`, `ReviewerName`, `ActiveYN`. Reviewers add and edit; Drivers read.
- scrReview has a 4th tab, **Daily review**. It lists drivers who submitted anything on the chosen date, matched by Created By email. The reviewer picks 1–5 stars and an optional comment, and Save creates the driver's row for that date or updates it.
- scrHome shows the driver their latest review from the last 7 days (not today) until they tap "Got it". Dismissals are saved on the phone ("fcSeenReview").
- A driver could read other drivers' reviews by opening the list in SharePoint. Per-item permissions would need a flow.

**Deferred:**
- Reading COF and blower due dates by scanning needs samples of both labels. A QR code or barcode on the label can use the existing scanner; printed text needs AI Builder (premium).
- Document scanning of invoices (edge detection) also needs AI Builder.

**Phase 2: Driver Assessment (not built):**
- A monthly fitness-to-drive assessment.
- New `Assessor` role: an AppRole choice plus a SharePoint group, with SyncAppUser extended.
- An assessments list and screen.
- A driver who fails can't start a checklist or run sheet that month.
- Assessors get a reminder (scheduled flow or banner) of drivers with no assessment this month.

---

## 6. Current state

### Done

- Three Forms import files generated; Driver Declaration and Run Sheet forms imported and configured (branching, required, number restrictions).
- SharePoint site "Fleet Operations" with Run Sheets, Run Sheet Details, Driver Declarations lists (and Pre-Trip Checks / Fleet Checklist).
- Driver Declaration flow and Run Sheet flow (17 stops) working; Pre-Trip flow fully mapped.
- Email templates drafted; test-data generator built.

### Drift between files and live system

| Item | Local file | Live |
| --- | --- | --- |
| Pre-trip end section | .docx: Driver Declaration (51 q); script: Site Engineer (52 q) | Site Engineer section, all Required |
| Run sheet stops | 18 stops, no numbers | 17 stops, "- n" titles, "(Sn)" question suffixes, extra sign-off/review questions |
| Stops list | "Run Sheet Stops" template with RunSheetID + StopOrder | "Run Sheet Details" with lookup, no Stop Order |

Update `build_forms.py` / `build_lists.py` before any re-import.

### Last open bugs

1. **Run sheet Trip Details merging** into the section description on Quick Import. Fix applied 20 Oct (explicit description line per section, answer lines removed, Word re-save) but **never confirmed by re-importing**. Live form is already built by hand, so only matters on re-import.
2. **END Mileage** not found in the live Return to CD section (22 Oct).
3. Review/approval and date questions in the live run sheet have **no list columns**.

### Open questions for the user

- Forms + Power Automate or Power Apps as the go-live driver front end? Is offline required?
- Pre-trip: how is the **truck** identified (QR code / link per truck / question / app dropdown)?
- Pre-trip: keep the Site Engineer section in the driver's form (Required), or move it to list columns / a Power Automate approval?
- Email alerts: will IT grant Send As on the shared mailbox, or use Teams posts?
- Is a Stop Order column needed on Run Sheet Details?

### Next steps

1. Ask the user where they left the Power Apps Fleet Checklist work and which track goes live.
2. Run a full end-to-end test of the Pre-Trip flow.
3. Turn off Required on the Site Engineer questions (or move them to the list / an approval).
4. Fix END Mileage and add list columns for the new run sheet sign-off fields; extend the flow.
5. Add the "No" alert (Teams or email once Send As is granted) and a flow-failure alert (configure "run after: has failed").
6. Index Date/Truck columns; create filtered views; add the office-only status columns.
7. Add a co-owner / service account to every flow.
8. Clean up test data, then pilot with 1–2 trucks.
9. Bring `build_forms.py` / `build_lists.py` in line with the live forms and lists; consider `git init`.

---

## 7. Gotchas and quick reference

### Gotchas

| Issue | What to do |
| --- | --- |
| Quick Import treats text right after a heading as the section description | Always put one description paragraph after each Heading 1 |
| Quick Import can't update a form | Import into a new form; then redo manual settings |
| Forms 200-question limit | Run sheet is at 197 (file) |
| Identical question names across stops | Unusable in Power Automate's picker: suffix "(Sn)" |
| Forms answers are text | `if(isFloat(x), float(x), null)`; add Number restrictions in Forms |
| "Send an email from a shared mailbox" → Unauthorized | Needs Send As from IT |
| Mail connector "Send an email notification (V3)" → 401 for new tenants | Don't use it; use Outlook "Send an email (V2)" or Teams |
| SharePoint internal names are fixed at creation | Short, no-space names; spaces become `_x0020_` |
| Breaking list permissions | Caused the Run Sheet Stops rebuild. Only stop inheriting with existing permissions **copied** (`setup_app_permissions.js` does this), so the flow owner and site owners keep access |
| Flow created from Studio's Power Automate pane ("Create from blank") | The app keeps the automatic name (`PowerAppV2->…`) even after renaming, so `<Flow>.Run` shows "'Run' is unknown". Remove from app, then Add flow again once it's named and saved |
| Long pre-filled links fail sign-in (AADSTS90015) | Keep under ~2,250 chars |
| Forms can't submit offline | Online only, or Power Apps offline |
| `npm install` / `pip install` fail (corporate SSL inspection) | Use stdlib Python; Playwright unavailable |
| No poppler / PIL; Read tool can't render PDFs | Extract PDF text with `pypdf`; the declaration scan is image-only |
| `python` on PATH resolves to another project's virtualenv (has `pypdf`, no `python-docx`) | Use stdlib or call that interpreter explicitly |
| Word 16 is scriptable via COM | Use for re-saving .docx |
| Files are not under git | Back up before regenerating (the build scripts overwrite their outputs) |

### Quick reference

```text
Build forms     python build_forms.py <out_dir> [fleet|run|decl]
Build lists     python build_lists.py <out_dir> ["Pre-Trip Checks" "Run Sheets" "Run Sheet Stops" "Driver Declarations"]
Import a form   forms.office.com → New Form → Quick import → .docx → review → Import
Create a list   SharePoint → + New → List → From Excel → pick the template → delete sample row
Email preview   open email-templates/preview.html in a browser
```

### Related folder: `fleet-checklist-org`

`C:\Users\Solomone.Tuilagivou\Documents\GitHub\fleet-checklist-org` is an **older snapshot (19 Oct 2026)**: the same SOP PDF plus first-generation import files. Its Pre-Trip .docx has the original 20-question checkbox layout (one checkbox + comments per section, Driver Declaration, office-use Site Engineer section); its Run Sheet .docx has 197 questions under the old title "Vehicle Run Sheet Checklist" with answer lines. No scripts, lists or flows. Treat it as superseded and don't edit it; this folder is the working copy.

---

## 8. Setting up the 23–24 Nov 2026 release

Do these in order. They cover everything from the meeting with Pawan's team: checklist v2, defects list, Trucks list, run sheet invoices, Daily review, draft and paging. Every script runs in the **browser console (F12) on the Fleet Operations site** while signed in as a site owner.

For each script:
- Run it once with `DRY_RUN = true` and read the summary.
- Then set `DRY_RUN = false` and run it again.
- Every script can be run again safely.

`scripts/setup_app_permissions.js` must already have run, because the new lists reuse its groups and permission levels.

### Step 1: SharePoint

| # | Script | What it does |
| --- | --- | --- |
| 1 | `scripts/create_checklist_v2_columns.js` (`MODE = 'create'`) | New Yes/No columns on Fleet Checklist (licence, driver's and passenger's side windows, cabin tilt, accident); index on Truck No |
| 2 | `scripts/create_checklist_defects.js` | **GF Fleet Checklist Defects** list (one row per item answered No), drivers add-only, own items |
| 3 | `scripts/create_trucks_list.js` | **GF Fleet Trucks** list: type, tyres, due dates, last odometer. Paste Krish's truck table into `CSV_TEXT` if you have it, or add trucks later |
| 4 | `scripts/create_runsheet_v2_columns.js` | `NoofInvoices` on Run Sheet Details; `RunKey` / `StopKey` on the Fleet Photos library |
| 5 | `scripts/create_daily_reviews.js` | **GF Fleet Daily Reviews** list |

Then have the office fill in each truck's **COF expiry, blower service due and truck service due** dates in GF Fleet Trucks.

### Step 2: Power Automate

1. **SaveFleetPhoto**: add two optional text inputs at the end, `RunKey` and `StopKey`. Map them in *Update file properties* (section 4.3).
2. **RunSheetSubmitted**: build it (section 4.5). It sends from your own mailbox until IT grants Send As on the shared mailbox.

### Step 3: Power Apps Studio

1. **Data sources:**
   - Add GF Fleet Checklist Defects, GF Fleet Trucks and GF Fleet Daily Reviews.
   - Refresh Fleet Checklist, Run Sheet Details and the photo library.
2. **Flows:** in the Power Automate pane, remove and re-add SaveFleetPhoto, then add RunSheetSubmitted.
3. **Screens:** paste each one over the old screen, checking the formula checker after each:
   1. `scrPhotos`
   2. `scrPreTrip`
   3. `scrRunSheet`
   4. `scrReview`
   5. `scrHome`
   6. `scrUsers`

   `scrPreTrip` is generated, so if a paste fails, fix `scripts/build_pretrip_screen.py` and regenerate. Don't hand-edit it.
4. **Optional, for testing in a browser:** Settings → turn on SaveData/LoadData for web players.
5. **Save**, then **Publish this version**.

### Step 4: Test

1. **Checklist, as a driver:**
   - Pages, Back and Next.
   - A No needs a comment.
   - The number of tyre photos matches the truck.
   - The due-date status shows.
   - The odometer warning appears.
   - Close the app halfway, then **Carry on** from Home.
   - Submit, then check the Fleet Checklist row, its defect rows and the photos.
2. **Run sheet, as a driver, in airplane mode:**
   - Add stops with invoice photos.
   - Turn signal back on, submit, and check the rows, the photos and the PDF email.
3. **As a reviewer:**
   - Sign off a checklist, including the weekly cabin tilt and greasing items. A second checklist for the same truck that week should show "conducted on … by …".
   - Verify a run sheet.
   - Give a driver a Daily review.
4. **As that driver the next day:** the Daily review banner shows on Home.

### Step 5: Waiting on others

- **Pawan:** approve [files/Fleet Checklist - item wording for approval.md](<files/Fleet Checklist - item wording for approval.md>), then run `create_checklist_v2_columns.js` with `MODE = 'rename'`. No app change is needed.
- **Krish:** the truck table, and which items apply only to Frozen trucks. Truck types are set in `scripts/checklist_items.json` (`truckType`); regenerate the screen after changing it.
- **COF and blower labels:** a photo of each, and the text your phone reads if they carry a QR code or barcode.
