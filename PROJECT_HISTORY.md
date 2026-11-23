# Fleet Checklist – Project History

Handover notes for whoever (or whichever AI assistant) picks this project up next.
Last updated: 20 Nov 2026.

## What this project is

Two paper forms used by the truck fleet are being turned into **Microsoft Forms**, so drivers can fill them in on their phones every day:

1. **Fleet Pre-Trip Checklist:** done by each driver before starting a vehicle.
2. **Vehicle Run Sheet:** one per trip, recording each delivery stop.

There is no app code yet, and the folder is not a git repository. Right now the work is building Word documents that Microsoft Forms **Quick Import** turns into forms (forms.office.com → New Form → Quick import → upload the .docx → review → Import).

## Files in this folder

| File | What it is |
| --- | --- |
| `DC 16.0 DRIVER RESPONSIBILITIES & CUSTOMER SERVICE V007 16.07.2025.pdf` | Source SOP (DC/16.0, version V007). **Page 9 (Appendix II)** is the Vehicle Run Sheet the form is built from. |
| `Fleet Pre-Trip Checklist - MS Forms import.docx` | Pre-trip checklist, laid out for Forms Quick Import. |
| `Vehicle Run Sheet - MS Forms import.docx` | Run sheet, laid out for Forms Quick Import. |
| `build_forms.py` | Script that generates both .docx files (plain Python, writes the Word XML directly; no python-docx needed). |

Run `python build_forms.py <out_dir> [fleet|run]` to build one or both forms. Since 20 Oct 2026 the run sheet is built into a temp folder, then opened in Word (COM) and saved again into this folder (Word 2013+ format), so the importer gets a standard Word package.

Environment notes (corporate Windows laptop):
- `npm install` fails with "self-signed certificate in certificate chain", so the Node `docx` package can't be used. Use Python with `python-docx` instead.
- `pdftoppm` (poppler) isn't installed, so PDFs can't be rendered to images (the Read tool can't show PDF pages either). Extract the PDF text with `pypdf`, which is installed; PIL and python-docx are not.
- Microsoft Word 16 is installed and scriptable via COM from PowerShell (`New-Object -ComObject Word.Application`).

## Current state of each form

### Fleet Pre-Trip Checklist (current version)

**Layout changed on 23 Oct 2026**, replacing the checkbox layout described further below:
- Each checklist item is now its own **Yes / No** question, like the driver declaration. The user chose Yes/No over OK/Not OK/N/A.
- Each section has a description line, then its items, then a "<Section> – comments" question.
- After the six sections come Odometer and Remarks, then Driver Declaration ("I agree", Driver full name, Date). 51 questions in total.
- The office-use section was removed. The Fleet Controller fills in Status, Approved By and Approved Date in the list.
- No answer lines.
- The list file (`Fleet Pre-Trip Checks - SharePoint list.xlsx`, 56 columns) now has one Yes/No Choice column per item. They're named with a section prefix ("Eng 01 Oil Levels", "Elec 10 Horn", "Brk 03 Tyres"…), so they group together and stay unique if SharePoint shortens the internal name.
- The old docx and xlsx are in the session scratchpad `backup\`.
- **The user edited the end of the live form (23 Oct 2026):**
  - The driver declaration ("I certify…", Driver full name, Date) was removed.
  - Section 9, "Declaration by the Site Engineer / Fleet Controller", was added: Approval for Delivery (Approved/Not Approved), Send for Repairs (Send/Don't Send), Manager / Warehouse Controller, Date of Declaration. All four are marked Required in Forms.
  - The list file was updated to match: Status, Approved By, Approved Date and Driver Agreed were replaced with those four columns plus Response ID (57 columns).
  - Driver Name and Check Date have to come from the Forms responder and the submission time.
  - `build_forms.py` was updated to match the live form.
- Guidance text from page 2 of the paper form (points 1–6, plus the capitalised "defects must be reported" paragraph) was given to the user to paste manually into a section description.

Earlier layout (superseded), kept for reference. The user asked for this layout, in this order:
- **No opening questions:** Site, Driver, Date, Truck Number and Fault were removed **on purpose**, at the user's request.
- **Section titles are plain text:** no "Section 1", "Section 2", and so on.
- **Each section has two questions:** one checkbox question ("select all that apply") listing every item from the paper form, then a separate comments question.

| Section | Questions |
| --- | --- |
| Engine and Transmission | 1. Checks completed (5 items: Oil Levels Engine Hydraulics (Top Level), Coolant Levels (Top Mark), Fan Belts (Alternator, Cooling Fan, A/C etc.), Oil / Water Leaks, PTO (Pump, Seals, Cable, Shaft, Augers, Universal Joint)) · 2. Comments |
| Electrical System | 3. Checkboxes (12 items, Battery Water Level → Cabin Dashboard Gauges) · 4. Comments |
| Body and Chassis | 5. Checkboxes (6 items) · 6. Comments |
| Brakes and Tyres | 7. Checkboxes (6 items) · 8. Comments |
| Safety Devices | 9. Checkboxes (6 items) · 10. Comments |
| General | 11. Checkboxes (5 items) · 12. Comments |
| Odometer and Remarks | 13–14 |
| Driver Declaration | 15–17 ("I agree", driver name, date) |
| Site Engineer / Fleet Controller | 18–20 (Approved for delivery / Send for repairs, name, date) |

Settings to make by hand after importing (Quick Import can't set them):
- Turn on **Multiple answers** and **Required** for questions 1, 3, 5, 7, 9 and 11.
- Change any date question that comes in as text to the **Date** type.

Open questions:
- **Last three sections:** they were kept, but it's unconfirmed whether the user wants them. "Keep only the section questions" might also mean ending the form after General.
- **Removed identifying fields:** removing truck number, driver and date means a response can't be tied to a truck unless drivers sign in with Microsoft 365 accounts (Forms then records who submitted it and when) or the truck is captured another way, for example a separate form link or QR code per truck. Raise this with the user before going live.

### Vehicle Run Sheet (current version)

Rebuilt from **page 9 of the V007 SOP**. The user's rule: **don't mention stop numbers** in question or section titles. Stops are told apart only by their Forms section number.

Every section is a Heading 1 followed by **one description line**, then its questions (see the bug note below for why).

- **Trip Details (questions 1–9):** Date, Truck #, Driver, Partner, Area, # Of Invoices, START Mileage, Expected Departure Time (CD), Expected Time of Arrival (CD).
- **Delivery Stop × 18 (questions 10–188):** one section per row of the paper sheet. Each asks, in column order: Time Out, Destination, # of Ctns, Arrive Time, Truck Temp (°C), Start Op Time, Complete Op Time, Duration (minutes), HSEQ Observations/Issues/Comments, and "Do you have another delivery stop?" (Yes/No). The 18th stop has no "another stop?" question.
- **Return to CD (questions 189–195):** Time truck returned, END Mileage, Balance invoice, Analog Temp., Temp. on Plug in, Qty on Balance Delivery, Invoice Balanced with Cashier (Yes/No).
- **Sign-off (questions 196–197):** Truck Driver's Name, Verified By: Team Leader Name.

Choices made in building it:
- **END Mileage** was moved from the header to Return to CD, because drivers only know it at the end of the run.
- **Dropped "Reviewed By / Approved By":** on V007 these are the SOP's own document approvals (Ronald Lal / Pawan Reddy), not a sign-off for each run.
- **Dropped the Sign / Date lines:** Forms records who submitted and when.
- **Question limit:** Forms allows **200 questions per form** and this one has 197, so there is room for only 3 more. If more are needed, cut a stop or a field. Duration, for example, could be worked out later from the start and complete times.

Settings to make by hand after importing:
- **Branching:** on each "Do you have another delivery stop?", send **Yes** to the next section and **No** to **Return to CD**.
- **Number restrictions:** use these for mileage, cartons and temperatures.
- **Times:** Forms has no time question type, so these are text questions ("hh:mm, 24-hour").

### Last open bug: Trip Details fields merging (fix unconfirmed)

The user reported that in Quick Import the **Trip Details fields came through as the section's description text, not 9 separate questions**. On 20 Oct 2026 the user confirmed the run sheet's Forms import still wasn't right (no details given) and asked to keep all 18 stop sections.
- **Probable cause:** Quick Import treats the text right after a section heading as that section's description. With no description of their own, the short question lines below the heading were absorbed into it.
- **Fixes applied to the Vehicle Run Sheet (20 Oct 2026):**
  1. Each section now has an explicit one-line description between its heading and its first question.
  2. The blank answer line (`________________`) under each text question was later **removed at the user's request** (run sheet only; `answer_lines: False` in the script). The section description lines are now what keeps Trip Details from merging.
  - Also at the user's request, the form title is now **"Driver Responsibilities and Customer Service"** and the intro reads "SOP DC/16.0 V007 Appendix II – Vehicle Run Sheet Checklist. …".
  3. "Date (date)" renamed to "Date".
  4. The file is saved again through Word.
  - Content is unchanged otherwise: it was re-checked against page 9 (18 stop rows confirmed from the page's table lines).
- **Fleet Pre-Trip Checklist:** not changed. It has no section descriptions yet; add them in `build_forms.py` if it shows the same problem.
- **Status:** **not yet confirmed** by re-importing.

To check it:
- Delete the broken form and import again into a new form; Quick Import can't update an existing form.
- On the preview screen, check that Trip Details shows **9 separate questions**.
- If it doesn't, split them in the preview, or add the 9 by hand as Text questions.

## How the user has asked for things (preferences)

- Follow the paper documents' wording and item lists exactly.
- **Section titles:** text only, with no "Section N" prefixes.
- **Stops:** no numbers in their titles.
- **Checkboxes:** each check group is one "select all that apply" question, required, with its own separate comments question.
- **When reporting back:** show the resulting question list so the user can check it.

## Data storage plan (discussed, not built)

Agreed direction for daily use across the fleet: **Microsoft Forms → Power Automate → SharePoint lists**.

- **Forms ownership:** create the forms under a Microsoft 365 group or Team (e.g. "Fleet Operations"), not a personal account, so the organisation owns them.
- **Power Automate:** a flow per form, triggered on each new response, creates a SharePoint list item. It can also alert the Fleet Controller in Teams or by email when a defect comment is filled in.
- **SharePoint site "Fleet Operations":**
  - **Pre-Trip Checks:** one row per checklist.
  - **Run Sheets:** one row per trip.
  - **Run Sheet Stops:** one row per stop, linked to its trip. The flow splits the repeating stop sections into rows using question order, since every stop has questions with the same names.
  - **Defect Photos library:** used only if photo upload is added.
  - **Office-only columns** (drivers never see these): Status (Open / Approved / Sent for repairs / Fixed), Actioned by, Date fixed.
- **Volume:** about 15,000 responses a year for 20 trucks. Index the **Date** and **Truck** columns and use filtered views (e.g. "Last 7 days") to stay clear of SharePoint's 5,000-item view limit.
- **Manager approval:** suggested moving this out of the driver's form into a Power Automate approval to the Fleet Controller.
- **Licensing:** drivers ideally have Microsoft 365 accounts (Frontline F1/F3 are cheaper). That records who submitted each response and allows photo upload. Check this with IT.
- **Possible extras:** photo upload after each defect comment (only on organisation-only forms), and a Power BI dashboard.
- **Rough setup effort:**
  - SharePoint site and lists: 1–2 hours.
  - Importing and configuring the forms: about 1 hour.
  - Each flow: about half a day.
  - QR codes per truck: about 1 hour.
  - Pilot with 1–2 trucks for a week.

## Update 21 Oct 2026: Power Apps + SharePoint chosen

- **Decision:** the user chose **Power Apps + SharePoint lists** over Forms + Power Automate. The Forms .docx files now serve as the spec for the questions.
- **Permissions:** the user couldn't create SharePoint lists or Teams at first, then got permission to create lists.
- **Third form added:** the **Fitness for Driving – Driver Declaration** (from the scanned `21102026103050-0001.pdf`).
  - It has its own Quick Import file: `Fitness for Driving Driver Declaration - MS Forms import.docx` (`python build_forms.py . decl`).
  - **Rebuilt on 23 Oct 2026** (it hadn't been imported yet). The file now has 19 questions:
    - No answer lines, and "Date (date)" renamed to "Date".
    - The sign-off's repeated name and date questions were removed.
    - The Supervisor section was removed; the supervisor fills in Supervisor Name/Date in the list instead.
    - The file was re-saved through Word COM like the run sheet. The old version is in the session scratchpad `backup\`.
  - **Working end to end (23 Oct 2026):** the form is imported, the "Driver Declaration → SharePoint" flow is built, and the Driver Declarations list is being populated. The flow is trigger → Get response details → Create item. The "answered No" alert Condition was still being added on 23 Oct.
  - **Email gotchas (23 Oct 2026):**
    - "Send an email from a shared mailbox" fails with Unauthorized, because the user lacks **Send As** on the shared mailbox. An IT request is needed.
    - The **Mail** connector ("Send an email notification (V3)") returns 401: Microsoft restricts it "for new tenants". **Don't use it.**
    - Use Office 365 Outlook **Send an email (V2)** from the user's own mailbox, or a Teams Flow bot post.
    - **Decision (23 Oct 2026): email alerts dropped for now.** They would have to come from a shared mailbox, and the user has no Send As permission; sending from their own work email isn't acceptable. Revisit if IT grants Send As. A Teams Flow bot post is the non-email alternative.
    - HTML email templates are in `email-templates/`: a compact alert, a detailed alert with Yes/No labels for all 14 declarations, and a flow-failure email. Open `preview.html` to see them.
  - Each of the 14 declarations is a required Yes/No question, so every line must be answered and any "No" is recorded.
- **Excel starter files for the lists:** built by `build_lists.py` (`python build_lists.py .`), one per list:
  - `Fleet Pre-Trip Checks - SharePoint list.xlsx`
  - `Vehicle Run Sheets - SharePoint list.xlsx`
  - `Vehicle Run Sheet Stops - SharePoint list.xlsx`
  - `Driver Declarations - SharePoint list.xlsx`
  
  Since 23 Oct 2026 the Pre-Trip Checks and Driver Declarations headers have spaces between words ("Check Date"), at the user's request (`SPACED` in `build_lists.py`). The Run Sheets files are unchanged. To rebuild only some files: `python build_lists.py . "Pre-Trip Checks" "Driver Declarations"`.

  How to use them: SharePoint → + New → List → From Excel. Each file has a table (the columns plus one sample row, to be deleted after import) and a "Column guide" sheet giving each column's label, SharePoint type and choices.
- **Column names:** short internal names with no spaces (e.g. `TruckNo`, `D01Licence`), because Power Apps uses the internal name, which can't change later.
- **Run sheet stops:** stored in their own list, linked by `RunSheetID` (the ID of the Run Sheets row) and `StopOrder`. This lets the app add any number of stops.
- **Pre-trip ticked items:** stored as multi-line text (items joined with "; "), one column per section, so the checklist items can change without changing the list.
- **Truck, driver and date:** the lists include these even though the Forms version dropped them. The app should fill them in (signed-in user, today's date, truck from a dropdown or QR code).

### Progress (21 Oct 2026)

- **SharePoint site "Fleet Operations"** exists with two lists:
  - **Run Sheets:** the built-in Title column is shown as "Truck #". Other columns: Run Date (Date), Driver, Partner, Area, No of Invoices, Start Mileage, Expected Departure, Expected Arrival, Time Returned, End Mileage, Balance Invoice, Analog Temp., Temp on Plug In, Qty on Balance Delivery, Invoice Balanced (Yes/No), Driver Name, Team Leader, Response ID, Active (Yes/No).
    - The six Number columns (invoices, both mileages, both temps, qty) are **Required**, and the matching form questions were made Required too.
    - The list itself may still be titled "Fleet Operations" (the user was told to rename it to Run Sheets).
    - There was a typo "Qty on Balance Recovery" (the user was told to rename it).
  - **Run Sheet Stops:** Title is shown as "Destination". Other columns: Run Sheet (Lookup → Run Sheets, Truck #), Stop Order, Time Out, No of Ctns, Arrive Time, Truck Temp, Start Op Time, Complete Op Time, Duration, HSEQ Comments, Active.
  - **Times are kept as Single line of text** for now. A date-time option, with time drop-downs in the form, was offered but not chosen.
- **Form:** branching and Required toggles are being set up by hand in Forms.
- **Flow "Run Sheet → SharePoint", Part A** (trigger → Get response details → Create item in Run Sheets) is built.
  - Gotchas:
    - Forms answers are text, so Number columns need `float(<answer>)` expressions.
    - Invoice Balanced uses `equals(<answer>,'Yes')`.
    - Required columns appear at the top of the Create item card.
  - Part A first failed because `float()` got a non-numeric answer. Fix: Forms **Restrictions → Number** on the numeric questions. After that it ran successfully twice.
  - Apply the same restriction to # of Ctns, Truck Temp and Duration in every stop section before building Part B.
- **Stop numbers added (21 Oct 2026):** the user added stop numbers to the stop questions directly in Forms. This relaxes the earlier "no stop numbers" rule, because identical names were unworkable in Power Automate's dynamic content picker.
  - The live form now differs from the generated .docx. Update `build_forms.py` to match if the form is ever re-imported.
- **Stop questions renamed (22 Oct 2026):** the 9 stop questions the flow reads now end in "(S1)"…"(S18)", so the picker can tell them apart. "Another stop?" is not renamed.
- **Part B, stop 1 works (22 Oct 2026):** both lists are being populated.
  - Number fields use `if(isFloat(x), float(x), null)`.
  - The condition is `empty(Destination (S1))` is equal to `false` (the expression `false`).
  - Remaining: copy the Stop block for S2–S18.
- **Part B, all stops built (22 Oct 2026):**
  - The live form has **17** stop sections, not 18. Its stop titles end in "- 1"…"- 17".
  - Stops 8–17 were generated from a copy of the Stop 7 block. The question IDs came from the form's question list (DevTools → Network). Each stop was then pasted with "Paste an action".
  - The working files were deleted afterwards because they held site, list and connection details.
- **Gaps found in the live form (22 Oct 2026):**
  - The end of the form now has **Date of Drive** and **Date Verified** in the sign-off, plus a **Review and Approval** section: Reviewed By, Date Reviewed, Approved By, Date Approved. None of these have Run Sheets columns yet.
  - **END Mileage** was not seen in the Return to CD section. Check where it is.

### Offline requirement (raised 22 Oct 2026)

The user wants drivers to be able to save data offline.
- **Microsoft Forms can't submit offline.** It can keep an unfinished response in the same browser, but submitting needs a connection.
- **Options:**
  - Accept online-only use and submit once back in signal.
  - Move the driver front end to a **Power Apps** canvas app with offline mode, which writes to the same SharePoint lists.
- Not decided yet. The user was given rough completion estimates:
  - Run sheet, online only: about 60%.
  - Both forms with a pilot: about 45%.
  - Including true offline: about 35%.

## Update 26 Oct 2026

- **Run Sheet flow: done** (confirmed by the user).
- **Pre-Trip flow:** every field is mapped into Create item on the Pre-Trip Checks list. A full test is still to run.
- All three forms now have working or mapped flows. Left to do: test the Pre-Trip flow, turn off Required on the Site Engineer questions (or let the manager fill them in the list), clean up test data, add a co-owner to the flows, run the pilot, and decide on offline use.

## Update 2 Nov 2026: Run Sheet stops rebuilt

- The user broke the permissions on the Run Sheet Stops list. They made a copy called **Run Sheet Details**, deleted the old list, and rebuilt the Run Sheet flow.
- **Run Sheet Details has a Run Sheet lookup column** (to Run Sheets, showing ID). Each stop's Create item sets `Run Sheet ID` = `outputs('Create_item')?['body/ID']` (Part A's new row), so stops link to their trip.
- **Stops 1–5** were built by hand. **Stops 6–17** were generated from a copy of Stop 5 plus the form's question list, then pasted in.
- Stop 5 had **no Stop Order field**, so the generated stops don't set one. The stops are created in sequence, so sorting by ID within a trip gives the order. Add a Stop Order column later if it's needed.
- The working files were deleted, and the clipboard and its history were cleared.
- **Test generator:** `Forms Test Data Generator.xlsx` (Setup: paste a pre-filled link; Tests: 20 random responses). Long pre-filled links fail through organisation sign-in (AADSTS90015) at about 2,250 characters, so blank long answers or use a short link. Playwright is blocked: pip fails on the corporate SSL inspection certificate.

## Mid-Nov 2026: Power Apps app (the go-live path)

Work moved to a **Power Apps canvas app** over the SharePoint lists on the Fleet Operations site. Every screen is kept as paste-in YAML in `screens/` (rules in `CLAUDE.md`; build detail in `PROJECT_HANDOVER.md`). The Forms + flows track still exists but is no longer the main path.

### Screens

| Screen | What it does |
| --- | --- |
| scrHome | Truck scan/entry, role-based buttons, offline banners |
| scrPreTrip | Fleet checklist form over the **Fleet Checklist** list (`field_1`–`field_55` plus new columns); also the manager's review/sign-off view |
| scrPhotos | Camera for odometer, accessory and defect photos (Take photo button, rounded frame) |
| scrRunSheet | One screen, three tabs (Trip / Stops / Return to CD) over **Run Sheets** + **Run Sheet Details**; works offline |
| scrDecl | Fitness for Driving declaration over **Driver Declarations** (14 checkbox statements) |
| scrReview | Review and sign-off for checklists, run sheets and declarations (Reviewer/Admin only) |

### Decisions and changes, in order

- **Run sheet in one screen** (not start/stop/end screens); unlimited stops (~70 per run is normal).
- **Yes/No answers are checkboxes**, ticked = Yes, unticked = No. Manager sign-off fields stay drop-downs. `Classic/CheckBox` has no `AccessibleLabel` (paste error PA2108).
- **Accessory Checks** (Krish Kumar, email 16 Nov): 3 dates + 15 Yes/No items + comments added to Fleet Checklist (internal names `Acc…`, see `files/Fleet Checklist - Accessory Checks columns.md`). Every item needs its own photo; Submit stays locked until the odometer photo and all 18 accessory photos are taken. Five items overlap existing checklist questions; still to confirm with Krish.
- **Next Service Due (km)** (`NextServiceDue`, number) added under the odometer.
- **Columns are created with scripts run in the browser console** on the site (`scripts/create_columns.js`, `create_accessory_columns.js`, `create_app_users.js`; dry run first). SharePoint adds new columns to the default view only; show them with *Show/hide columns*.
- **Delegation fix:** stops were filtered on the `RunSheet` lookup, which SharePoint can't do server-side (only the first 500 rows would be searched). Added a number column **`RunSheetID`** to Run Sheet Details; the app writes and filters on it. Older stops without it don't show.
- **Roles:** new list **GF Fleet Checklist App Users** (Name, `UserEmail` lower case, `AppRole` Admin/Reviewer/Driver, `ActiveYN`). Roles stack (Reviewer ⊃ Driver, Admin ⊃ Reviewer). First users: the project owner (Admin) and the five recipients of the 16 Nov meeting-notes email (Reviewer, to be confirmed). App Users has its own permissions: groups Read, owners edit. A setup guide was published as a private artifact ("Fleet App Access Setup").
- **Sharing:** publishing doesn't expose the app; only people it's shared with can open it. Share with named people (not "Everyone" or the site's big groups).
- **SaveFleetPhoto flow** (Power Automate, called from scrPreTrip after submit, once per photo) already exists; it wasn't documented. Its inputs are in `PROJECT_HANDOVER.md` 4.3. Which library it saves to still needs confirming.
- **Offline (run sheet only):** trip and stops are saved on the phone (`SaveData`) and uploaded by an Upload button / automatically on the next save when there's signal. Role is cached so the app opens offline. Needs the **Power Apps mobile app** (not the browser) and one online launch first. Checklist and declaration still need signal (photos make them the bigger job).
- **Look and feel:** taller page headers on all screens; more space around checklist card titles.

### Lists the app uses

| List | Notes |
| --- | --- |
| Fleet Checklist | `field_N` columns from the Excel import + `Acc…` accessory columns + `NextServiceDue`. field_52/53 = manager drop-downs |
| Run Sheets | Status choices: Open, Closed, In Progress |
| Run Sheet Details | Lookup `RunSheet` + number `RunSheetID` (used by the app) |
| Driver Declarations | field_3–field_16 = 14 statements ("Yes"/"No" text) |
| GF Fleet Checklist App Users | Roles. Both Fleet App groups have Read; only the SyncAppUser flow writes to it |

## Update 23 Nov 2026: app-managed access, drivers add-only

- **Why:** a colleague's phone couldn't open screens until they were given list access. Power Apps opens SharePoint as the signed-in user, so every driver needs list access. The decision was to let drivers **add** records but not see others' records, and **not edit or delete** (user's decision).
- **Groups and permissions** (`scripts/setup_app_permissions.js`, run 23 Nov): permission levels **Fleet App Driver** (view + add, no edit/delete) and **Fleet App Reviewer** (view, add, edit + Override List Behaviors, no delete). Groups **Fleet App Drivers** / **Fleet App Reviewers**, granted on Fleet Checklist, Run Sheets, Run Sheet Details and Driver Declarations, with existing permissions **copied** first. Item-level permissions "read own items" on those four. Both groups have Read on App Users. Existing app users were put in the groups.
- **Manage users screen** (`scrUsers`, Admin only, button on scrHome) calls the **SyncAppUser** flow. The flow checks the caller is an active Admin, creates or updates the App Users row, and moves the person into the right group through the SharePoint REST API, so **no email is sent**. Tested 23 Nov: a colleague was added as Driver.
- **Run sheet is add-only:** nothing is written until Submit; then the trip (Status Open) and its stops are created as new rows. Sent stops can't be edited in the app. "In Progress" is no longer written, so Team Leaders don't see a run until it's submitted.
- **Lessons from building the flow:** rename actions before referencing them; fill fields from the Expression tab only (SharePoint tokens add Apply to each loops); make both Respond steps identical by copying; a flow created from Studio's pane keeps an automatic `PowerAppV2->…` name in the app (fixed with Save As + re-add); one-line YAML values containing `: ` break the paste (PA1001).

## Update 23 Nov 2026 (later): meeting with Pawan's team

- **Checklist:**
  - Reordered: Licence and Odometer, then Cabin, Electrical, Tyres, Leaks and Fluid Levels, and the rest.
  - Reworded so each item states what the driver should see, in 7 words at most, e.g. "Battery water at top mark". There's no instruction line, by the user's decision after a first, longer draft. The wording goes to Pawan for approval (`files/Fleet Checklist - item wording for approval.md`).
  - Every item is now an explicit **Yes / No** with a comment on No. This replaces the 19 Nov rule where ticked = Yes and unticked = No.
  - Comments on No moved from one `<field>Cmt` column per item to a child list, **GF Fleet Checklist Defects** (one row per No, Status Open/Fixed), by the user's decision: 60-odd mostly empty columns on Fleet Checklist, and the list doubles as a defect register.
  - Added: licence, glass checks for the driver's and passenger's side windows (the existing windscreens item stays), net/gross weight photo, accident imagery, and truck profile photos (Front, Rear, Left, Right).
  - Money Box removed. One photo per tyre.
  - Cabin tilting and underneath greasing are weekly and reviewer-only. The app shows "inspection conducted on … by …" when the truck was already done that week (user's design).
  - Truck number locked once set on Home. Site required.
  - The screen is now generated from `scripts/checklist_items.json`.
- **Trucks list** (GF Fleet Trucks) for truck type and number of tyres. Krish to send the full table. Which items each truck type sees is still to confirm.
- **Run sheet:**
  - Actual departure time only.
  - HH : MM time entry.
  - Arrive time first, "time left the premises" last.
  - Invoices per stop, each with an in-app photo. No gallery, by the user's decision.
  - Photos upload whenever there's signal.
  - A planned **RunSheetSubmitted** flow emails a PDF of all invoices.
- **Daily review:** reviewers give each driver 1–5 stars a day, with an optional comment. The driver sees it on Home on their next shift (named "Daily review" by the user).
- **Deferred:**
  - Reading COF and blower dates by scanning (needs label samples; printed text would need AI Builder).
  - Invoice document scanning.
  - Phase 2 Driver Assessment with an Assessor role.
- The cut-off meeting note about truck numbers was dropped.
- **Four checklist improvements (user's choice, same day):** COF / blower / truck service dates read from the Trucks list with an Expired / Due soon / OK status (date picker + photo only as fallback); an odometer sanity warning against the truck's last reading (new UpdateTruckOdometer flow keeps it current); a draft saved on the phone with Carry on / Discard on Home, plus a local retry queue for defect rows and photos that fail after save; and one section per page with Back / Next and a progress bar.

## Suggested next steps

1. Run the new scripts:
   - `create_checklist_v2_columns.js`
   - `create_trucks_list.js`
   - `create_runsheet_v2_columns.js`
   - `create_daily_reviews.js`
2. Add the new lists as data sources and refresh Fleet Checklist, Run Sheet Details and the photo library.
3. Add the two SaveFleetPhoto inputs, then re-add the flow in the app.
4. Paste every screen and test on a phone, including airplane mode for the run sheet.
5. Build the RunSheetSubmitted flow.
6. Send the wording document to Pawan. Once approved, run the column script in rename mode.
7. Get the truck table from Krish, and photos of the COF and blower labels.
8. Confirm roles with Krish, then share and publish (see the access guide).
9. Add a photo strip to the review screen.
10. Krish's remaining meeting items: Trade Issue email (total vs actual quantity), Fleet Checklist to Excel/MEX email.
11. Decide whether the fleet checklist and declaration need to work offline too.
12. Rerun `create_trucks_list.js` (new date and odometer columns, Reviewers get edit), have the office fill in the due dates, and build the UpdateTruckOdometer flow (handover 4.6).
