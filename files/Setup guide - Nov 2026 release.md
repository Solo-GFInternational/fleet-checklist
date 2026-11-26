# Setup guide: Nov 2026 release

Step-by-step setup for everything built after the 23 Nov 2026 meeting with Pawan's team:

- **Checklist:** the new checklist with Yes/No answers and comments, the defects list, the Trucks list, the draft saved on the phone, and one section per page.
- **Run sheet:** invoice photos, attached to the email from your existing **Run Sheet - Submission email** flow.
- **Review:** the Daily review.

Work through the steps in order. Each step links to where its background lives, but everything you need to do is in this guide.

Every step is a tick box. To tick one, change `- [ ]` to `- [x]` in VS Code. With the *Markdown All in One* extension, put the cursor on the line and press **Alt+C**. The ticks then show in the preview (**Ctrl+Shift+V**) and on GitHub.

| Step                 | Where                                        | Who                                  |
| -------------------- | -------------------------------------------- | ------------------------------------ |
| 0. Before you start  | —                                           | You                                  |
| 1. SharePoint        | Browser console on the Fleet Operations site | Site owner                           |
| 2. Power Automate    | Power Automate                               | Flow owner                           |
| 3. Power Apps Studio | Power Apps                                   | App owner                            |
| 4. Test              | Phone and browser                            | You, plus a test driver and reviewer |
| 5. Waiting on others | —                                           | Pawan, Krish, office                 |

---

## Step 0: Before you start

- [ ] **1.** **Permissions setup has run.** `scripts/setup_app_permissions.js` must already have run on the site. It creates the groups **Fleet App Drivers** and **Fleet App Reviewers** and the permission levels **Fleet App Driver** and **Fleet App Reviewer**, which the new lists reuse.
  - If it hasn't, run it first, the same way as the scripts in Step 1.
  - Background: [PROJECT_HISTORY.md](../PROJECT_HISTORY.md) "Update 23 Nov 2026: app-managed access".
- [ ] **2.** **The branch is merged.** Merge `meeting-changes-2026-11` into `main`, or work from that branch, so the files you paste are the latest.
- [ ] **3.** **Pick a quiet time.** Pasting screens changes the live app only after **Publish**, but the SharePoint scripts change the lists straight away.

### How to run a setup script (same for every script in Step 1)

- [ ] **1.** Open the **Fleet Operations** SharePoint site in **Edge or Chrome**, signed in as a **site Owner**. Any page of the site will do.
- [ ] **2.** Press **F12** and open the **Console** tab.
- [ ] **3.** Open the script file in VS Code, select everything (**Ctrl+A**) and copy it (**Ctrl+C**).
- [ ] **4.** Leave `const DRY_RUN = true;` near the top for the first run.
- [ ] **5.** Click in the console, paste (**Ctrl+V**) and press **Enter**. If the console refuses, type `allow pasting`, press **Enter**, then paste again.
- [ ] **6.** Read what it prints between the `=====` lines. A dry run only lists what it **would** do.
- [ ] **7.** If that looks right, change the line to `const DRY_RUN = false;`, paste the whole file again and press **Enter**.
- [ ] **8.** Copy the output between the `=====` lines and keep it, for example in your notes.

What the output can tell you:

| Output                                           | What it means                                                       | What to do                                             |
| ------------------------------------------------ | ------------------------------------------------------------------- | ------------------------------------------------------ |
| `skip … (exists)`                             | Already done on an earlier run                                      | Nothing. Every script can be run again safely          |
| `SKIPPED … group or permission level missing` | `setup_app_permissions.js` hasn't run                             | Run it, then run this script again                     |
| `DO BY HAND …`                                | SharePoint wouldn't take the "own items only" setting from a script | Follow the List settings steps it prints               |
| `FAILED …`                                    | Something went wrong                                                | Copy the whole output and look into it before going on |

---

## Step 1: SharePoint

Run these in order, each one dry run first.

### 1.1 Checklist columns: `scripts/create_checklist_v2_columns.js`

- Keep `const MODE = 'create';`.
- **What it does:**
  - Adds the new Yes/No columns to **Fleet Checklist**: `LicenceValid`, `CabGlassDriver`, `CabGlassPassenger`, `CabTilt`, `AccidentDamage`.
  - Indexes `field_1` (Truck No), which the weekly cabin tilt / greasing look-up needs.
- **Later:** once Pawan approves the wording, run it again with `MODE = 'rename'` (see Step 5).

- [ ] Dry run (`DRY_RUN = true`): output looks right
- [ ] Real run (`DRY_RUN = false`): no `FAILED` lines
- [ ] Output saved
- [ ] *(Later, after Pawan approves)* Run again with `MODE = 'rename'`

### 1.2 Defects list: `scripts/create_checklist_defects.js`

- **List:** creates **GF Fleet Checklist Defects**, one row per checklist item answered No.
- **Columns:** Item (the wording), `ChecklistID`, `Truck`, `ItemField`, `Comment`.
- **Permissions:**
  - Drivers can add rows but not edit them, and see only their own.
  - Reviewers see and edit all rows.
  - Nobody in the app groups can delete.

- [ ] Dry run (`DRY_RUN = true`): output looks right
- [ ] Real run (`DRY_RUN = false`): no `FAILED` lines
- [ ] Output saved

### 1.3 Trucks list: `scripts/create_trucks_list.js`

- **List:** creates **GF Fleet Trucks**, one row per truck.
- **Columns:**
  - Title: the truck number, as "FJ 101"
  - Truck type: Ambient or Frozen
  - Make, as "Isuzu FTR + Freezer Body"
  - Number of tyres
  - Active
  - COF expiry, Blower service due, Truck service due
- **Permissions:** Drivers can read; Reviewers can edit, so the office keeps the dates current.
- **Paste the trucks into the script:** copy `files/Fleet Trucks.csv` (the 33 trucks; kept on the project owner's PC, not in git) between the backticks of `CSV_TEXT`. It comes from the office's truck workbook (Details and Tires sheets matched by registration). It fills Truck type (Dry → Ambient, Freezer → Frozen), Make, Number of tyres (the Tires count minus the spare) and COF expiry. Blower service due and Truck service due are left for reviewers.
  - When the office sends a new workbook: save it as `files/Truck Details updated.xlsx`, run `py -3 -I scripts/merge_truck_details.py "files/Truck Details updated.xlsx" files`, read its `NOTE` lines, and paste the new `files/Fleet Trucks.csv` between the backticks of `CSV_TEXT`.
  - Trucks already in the list are updated with the sheet's values (`UPDATE_EXISTING = true`). Blank cells never clear anything, and the two service dates are never touched.
- **If you ran an earlier version** that created `LastOdometer` / `LastOdometerDate`, delete those two columns: List settings → click the column → **Delete**. The app no longer uses them.

- [ ] Dry run (`DRY_RUN = true`): output looks right
- [ ] Real run (`DRY_RUN = false`): no `FAILED` lines
- [ ] Output saved

### 1.4 Run sheet columns: `scripts/create_runsheet_v2_columns.js`

- Adds `NoofInvoices` ("No of invoices") to **Run Sheet Details**.
- Adds `RunKey` and `StopKey` (text) to the **Fleet Photos** library.
- Adds `NoofStops`, `NoofInvoicePhotos` and `RunKey` to **Run Sheets**. The app fills these in when it sends a run, so the submission email flow knows what to wait for.
- Indexes `RunKey` on Fleet Photos and `RunSheetID` on Run Sheet Details. The flow searches on both, and Fleet Photos will pass 5,000 files.

- [ ] Dry run (`DRY_RUN = true`): output looks right
- [ ] Real run (`DRY_RUN = false`): no `FAILED` lines
- [ ] Output saved

### 1.5 Daily review list: `scripts/create_daily_reviews.js`

- **List:** creates **GF Fleet Daily Reviews**.
- **Columns:** Driver, `DriverEmail`, `ReviewDate`, `Stars` (1–5), `Comment`, `ReviewerName`, Active.
- **Permissions:** Reviewers add and edit; Drivers read.

- [ ] Dry run (`DRY_RUN = true`): output looks right
- [ ] Real run (`DRY_RUN = false`): no `FAILED` lines
- [ ] Output saved

### 1.6 By hand in SharePoint

- [ ] **1.** **Ask the office to fill in each truck's dates** in GF Fleet Trucks: COF expiry, Blower service due, Truck service due. The checklist shows them as Expired / Due within 30 days / OK. When a truck has no date, the driver types it and takes a photo instead.

---

## Step 2: Power Automate

### 2.1 SaveFleetPhotos: add two inputs

The run sheet now uploads invoice photos through this flow, tagged with the run and the stop. Background: [PROJECT_HANDOVER.md §4.3](../PROJECT_HANDOVER.md#43-power-apps-flow-savefleetphoto).

- [ ] **1.** Power Automate → **My flows** → **SaveFleetPhotos** → **Edit**.
- [ ] **2.** Click the trigger card, **When Power Apps calls a flow (V2)**.
- [ ] **3.** **+ Add an input** → **Text** → name it `RunKey`. Then **⋯** on that input → **Make the field optional**.
- [ ] **4.** **+ Add an input** → **Text** → name it `StopKey` → **⋯** → **Make the field optional**.

  They must come **after** the six existing inputs, in this order.
- [ ] **5.** Open the **Update file properties** action. Fill **Run key** with `RunKey` and **Stop key** with `StopKey`, from the trigger's dynamic content. Tokens from the trigger are fine here; it's the SharePoint tokens that add unwanted loops.
- [ ] **6.** **Save**.

The checklist's existing six-input call keeps working, because the new inputs are optional. You'll remove and re-add the flow in the app in Step 3.

### 2.2 Run Sheet - Submission email: wait for everything, attach the invoice photos

Your existing flow, **Run Sheet - Submission email**, stays the submission email. Its trigger, its trigger conditions, its stops table with ⚠ flags and its email layout don't change.

Three things are added or changed:

- [ ] **1.** **Wait for the whole run.** The app creates the trip first, then the stops one by one, then any invoice photos still waiting. The fixed 1-minute **Delay** becomes a loop that waits until every stop and every invoice photo has arrived, using the new `NoofStops` and `NoofInvoicePhotos` columns the app now fills in.
- [ ] **2.** **Invoice photos on the email.** The run's invoice photos (the newest copy of each) are attached as JPEGs, as many as fit in about 19 MB. The email says how many there are and how many are attached, and links to Fleet Photos filtered to that run, so every photo can be opened.
- [ ] **3.** **Mark as emailed once.** Your **Update item** currently sits inside a *For each* over the stops, so it updates the same run once per stop (about 70 times). It moves out of the loop.

Background: [PROJECT_HANDOVER.md §4.5](../PROJECT_HANDOVER.md#45-run-sheet-submission-email-flow).

The flow uses only the SharePoint and Office 365 Outlook connections it already has. **There's no invoice PDF:** every standard way to make one needs something this tenant doesn't have. OneDrive *Convert file* needs a working OneDrive connection, Word Online *Convert to PDF* isn't in the M365 licence, and SharePoint's own `?format=pdf` replies with a redirect the connector can't follow (all tried 24 Nov 2026). The others are premium connectors.

#### Option A (recommended): build it with the script and import it

`scripts/build_submission_email_flow.py` takes the package you exported from your flow and writes a new package with every change in this section already built in. Your trigger, its conditions, the stops table and your email layout are copied over unchanged.

**Inputs to fill in.** Open `scripts/build_submission_email_flow.py` and check the **INPUTS** block at the top:

| Input                                           | Default                           | What to check                                                                                                         |
| ----------------------------------------------- | --------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `FLOW_NAME`                                     | `Run Sheet - Submission email v2` | Any name; the import creates it next to your current flow                                                             |
| `PHOTOS_LIBRARY`                                | `Fleet Photos`                    | The photo library's name exactly as SharePoint shows it                                                               |
| `PHOTOS_URL_NAME`                               | `Fleet Photos`                    | Open the library and look at the address bar: the part after the site name (spaces show as `%20`), for the email link |
| `FAILURE_EMAIL`                                 | empty (off)                       | Your email address, if you want to be told when the flow fails                                                        |
| `WAIT_MINUTES`, `MAX_CHECKS`, `ATTACH_LIMIT_MB` | 2, 30, 19                         | Leave as they are unless you want a shorter or longer wait                                                            |

You don't need to fill in the site address, list IDs or email recipients. The script reads them from your export.

- [ ] **A1.** Run it (from the repo folder, in a terminal):
  ```
  py -3 -I scripts/build_submission_email_flow.py files "files/Solo_20261123212614.zip"
  ```
  It writes `files/Run Sheet - Submission email v2 - import package.zip`. Zip files in `files/` are git-ignored, because they contain your site address and list IDs.
- [ ] **A2.** Delete any earlier imported **Run Sheet - Submission email v2** (**⋯ → Delete**), so only one copy exists. Then Power Automate → **My flows** → **Import** → **Import Package (Legacy)** → **Upload** → pick the new .zip.
- [ ] **A3.** On the import page:
  - Next to the flow, click **Update** under *Import setup* → **Create as new** → **Save**.
  - For each connection (SharePoint, Office 365 Outlook), click **Select during import** → pick yours → **Save**.
  - Then click **Import**.
- [ ] **A4.** Open the new flow → **Edit** and check that no action shows a red error. If **Check photos** or **Get invoice files** complains about the library, pick **Fleet Photos** from its **Library Name** drop-down. Then **Save**.
- [ ] **A5.** Turn the **new** flow **on** and your **old** "Run Sheet - Submission email" **off** (**⋯ → Turn off**). If both are on, both send.
- [ ] **A6.** Test as in step 8 below. If anything is wrong, turn the new flow off and the old one back on while it's fixed.

Steps 0–8 below are the same changes done by hand. You only need them if the import fails, or to understand what the script built.

#### Option B: make the changes by hand

**How to read the steps below**

- **Click** means a button or menu in Power Automate.
- `Code like this` is text you type or paste.
- An **expression** is entered by clicking the field → the **fx** (Expression) tab → pasting → **Add**. Never pick SharePoint "dynamic content" tokens for these, because they add automatic *Apply to each* loops.
- **Rename every new action straight after adding it**, exactly as written: **⋯** on the action → **Rename**. The expressions refer to actions by these names.
- Wherever a step asks for **Site Address**, pick the Fleet Operations site.

#### 0. Before you start

- [ ] **1.** Step 1.4 has run. Run Sheets now has `NoofStops`, `NoofInvoicePhotos` and `RunKey`, and Fleet Photos has `RunKey` (indexed) and `StopKey`.
- [ ] **2.** **Keep a backup:** open the flow → **⋯ → Save As** → `Run Sheet - Submission email (backup)` → **Save**. Then turn the backup **off** (**⋯ → Turn off**) so it never sends.
- [ ] **3.** Open the original: **My flows** → **Run Sheet - Submission email** → **Edit**.

#### 1. Variables, at the top

- [X] **1.** Hover between the trigger and **Delay** → **+** → **Add an action** → **Initialize variable**. Add these, renaming each one as shown:

  | Rename to            | Name            | Type    | Value                                                 |
  | -------------------- | --------------- | ------- | ----------------------------------------------------- |
  | `Init stopsFound`  | `stopsFound`  | Integer | `0`                                                 |
  | `Init photosFound` | `photosFound` | Integer | `0`                                                 |
  | `Init tries`       | `tries`       | Integer | `0`                                                 |
  | `Init seen`        | `seen`        | Array   | `[]`                                                |
  | `Init keep`        | `keep`        | Array   | `[]`                                                |

- [ ] **1b.** Two more (added 24 Nov 2026). If you added `Init html` earlier, delete it (**⋯ → Delete**); there's no PDF to build any more.

  | Rename to            | Name            | Type    | Value |
  | -------------------- | --------------- | ------- | ----- |
  | `Init photoFiles`  | `photoFiles`  | Array   | `[]`  |
  | `Init photoChars`  | `photoChars`  | Integer | `0`   |

  Initialize variable only works at the top level, never inside a loop or condition, so put them all directly under the trigger.

  **Name** (inside the action) must be typed exactly, including capitals, because later steps use `variables('stopsFound')` and so on. **Rename to** is the action's title (**⋯ → Rename**). It's optional for these, but for every other new action in this guide the rename is required, because expressions refer to those actions by name.

#### 2. Replace the Delay with a wait loop

- [X] **2.** On **Delay**: **⋯ → Delete**.
- [X] **3.** Under the variables: **+** → **Control – Do until**. Rename it `Wait for the run`.

  - **Loop until:** click **Edit in advanced mode** (or the expression editor) and paste:
    ```
    @or(and(greaterOrEquals(variables('stopsFound'), int(coalesce(triggerOutputs()?['body/NoofStops'], 0))), greaterOrEquals(variables('photosFound'), int(coalesce(triggerOutputs()?['body/NoofInvoicePhotos'], 0)))), greaterOrEquals(variables('tries'), 30))
    ```
  - **Change limits:** **Count** `40`, **Timeout** `PT2H`.

  It stops when every stop and every invoice photo is in, or after 30 checks (about an hour), whichever comes first. Runs from before this release have no `NoofStops`, so they don't wait at all, as today.
- [X] **4.** **Inside** the Do until, in this order:

  - [X] **1.** **Control – Delay**, renamed `Wait a minute`: **Count** `2`, **Unit** Minute.
  - [X] **2.** **SharePoint – Get items**, renamed `Check stops`:
    - **List Name:** Run Sheet Details
    - **Filter Query:** `RunSheetID eq ` + expression `triggerOutputs()?['body/ID']`
    - **Top Count:** `500`
  - [X] **3.** **SharePoint – Get files (properties only)**, renamed `Check photos`:
    - **Library Name:** Fleet Photos
    - **Filter Query:** `RunKey eq '` + expression `coalesce(triggerOutputs()?['body/RunKey'], 'none')` + `'`
    - **Top Count:** `500`
  - [X] **4.** **Data Operation – Select**, renamed `Photo slots`:
    - **From:** expression `body('Check_photos')?['value']`
    - Click **Switch Map to text mode** (the **T** icon). **Map:** expression `concat(item()?['StopKey'], '|', item()?['Item'])`
  - [X] **5.** **Set variable** `stopsFound` = expression `length(body('Check_stops')?['value'])`
  - [X] **6.** **Set variable** `photosFound` = expression `length(union(body('Photo_slots'), body('Photo_slots')))`. Counting each slot once means a retaken photo isn't counted twice.
  - [ ] **7.** **Increment variable** `tries` by `1`

#### 3. Keep your stops lookup and condition

- [ ] **5.** Your **Get items** now sits below the Do until. Leave it as it is. Because it runs after the wait, it finds every stop.
- [ ] **6.** Your **Condition** (stops > 0) stays. Its **False** branch (Terminate) stays.

#### 4. Collect the invoice photos, inside your Condition's True branch, before Send an email

- [ ] **7.** In **True**, hover above **Send an email (V2)** → **+** → add these in order:

  - [ ] **1.** **SharePoint – Get files (properties only)**, renamed `Get invoice files`:

    - **Library Name:** Fleet Photos
    - **Filter Query:** `RunKey eq '` + expression `coalesce(triggerOutputs()?['body/RunKey'], 'none')` + `'`
    - **Order By:** `Created desc`
    - **Top Count:** `500`
  - [ ] **2.** **Control – Apply to each**, renamed `For each file`:

    - **Select an output:** expression `body('Get_invoice_files')?['value']`
    - **⋯ → Settings → Concurrency control: On, Degree of parallelism: 1 → Done**
    - Inside it: **Condition**, renamed `New slot`. Left box expression: `contains(variables('seen'), concat(items('For_each_file')?['StopKey'], '|', items('For_each_file')?['Item']))`. Operator **is equal to**. Right box expression: `false`.
    - In its **True**, add two actions:
      - [ ] **1.** **Append to array variable** `seen`, expression `concat(items('For_each_file')?['StopKey'], '|', items('For_each_file')?['Item'])`
      - [ ] **2.** **Append to array variable** `keep`, expression `items('For_each_file')`

    The newest copy of each invoice wins, so a retake replaces the first photo.
  - [ ] **3.** **Control – Apply to each**, renamed `For each invoice`:

    - **Select an output:** expression `reverse(variables('keep'))` (oldest first, so the photos follow the stops)
    - Concurrency **On, 1**
    - Inside it:
      - [ ] **1.** **SharePoint – Get file content**, renamed `Get invoice content`. **File Identifier:** expression `items('For_each_invoice')?['{Identifier}']`
      - [ ] **2.** **Condition**, renamed `Fits in email`. Left box expression: `add(variables('photoChars'), length(string(body('Get_invoice_content')?['$content'])))`. Operator **is less than**. Right box: `26563925` (about 19 MB once encoded; Outlook rejects much bigger emails).
      - In its **True**, add two actions:
        - [ ] **1.** **Append to array variable** `photoFiles`, renamed `Add photo file`. Value (paste as is; the two `@{…}` parts become expressions):
          ```
          {"Name": "@{concat(replace(replace(coalesce(items('For_each_invoice')?['Item'], 'Invoice'), ' · ', '_'), ' ', ''), '.jpg')}", "ContentBytes": "@{body('Get_invoice_content')?['$content']}"}
          ```
        - [ ] **2.** **Increment variable** `photoChars`, renamed `Count photo size`, by expression `length(string(body('Get_invoice_content')?['$content']))`

  Photos are named after their slot, e.g. `Stop3_Invoice2.jpg`. Once the email is full, the rest are left off and reached through the link.

#### 5. Your Send an email (V2): invoice line and attachments

- [ ] **8.** Open **Send an email (V2)** and leave To, Subject and the body as they are, except for two changes.
  - [ ] **1.** **Body:** switch to code view (**</>**). Just before the line `<p>Waiting for Team Leader verification in the Fleet Checklist app.</p>`, paste the line below. Type your Fleet Operations site address in place of `<site>`; it goes in the flow only, never in the repo.
    ```
    <p><b>Invoices:</b> @{length(variables('keep'))} photos, @{length(variables('photoFiles'))} attached. <a href="<site>/Fleet%20Photos/Forms/AllItems.aspx?FilterField1=RunKey&amp;FilterValue1=@{encodeUriComponent(coalesce(triggerOutputs()?['body/RunKey'], 'none'))}">Open this run's invoice photos in Fleet Photos</a>.</p>
    ```
  - [ ] **2.** **Show advanced options → Attachments:** click the **T** / **Switch to input entire array** icon, then the expression `variables('photoFiles')`.

#### 6. Mark as emailed once

- [ ] **9.** Drag **Update item** out of **For each**, to just below **Send an email (V2)**, still inside True. If drag-and-drop doesn't work: **⋯ → Copy to my clipboard** on Update item → **+** below Send an email → **My clipboard** → pick it → then delete the original.
- [ ] **10.** Delete the now-empty **For each**.
- [ ] **11.** In the moved **Update item**, **Id** must still be the trigger's ID. Leave its fields (No of invoices, Start mileage, Submission Emailed = Yes) as they are.

#### 7. Tell yourself if it fails (optional, recommended)

- [ ] **12.** Below the Condition (outside it): **Office 365 Outlook – Send an email (V2)**, renamed `Tell owner it failed`.
  - **To:** your address
  - **Subject:** expression `concat('Run sheet submission email failed for run ', triggerOutputs()?['body/ID'])`
  - **⋯ → Configure run after:** untick **is successful**, tick **has failed** and **has timed out** → **Done**.

#### 8. Save and test

- [ ] **13.** **Save** (top right).
- [ ] **14.** Submit a test run from the app with a few stops and an invoice photo on each. Or run `scripts/create_test_runsheet.js`: it sends a submitted trip, its stops and generated JPEG invoice photos (coloured "TEST INVOICE" pages, plus one retake) the way the app does. With `PHOTOS_FIRST = false` the photos arrive a minute late, so the wait loop is tested too.
- [ ] **15.** Open the flow's **Run history** and check:
  - **Wait for the run** looped until the stops (and photos) were all found.
  - The email lists every stop, says "Invoices: N photos, N attached", and has the JPEGs attached (a retaken invoice only once, the newest copy).
  - The link opens Fleet Photos showing only that run's photos.
  - **Submission Emailed** is Yes on the run, and it was updated once.

**If fewer photos are attached than taken,** they didn't fit in about 19 MB together; the link shows them all. **If none are attached,** check **Get invoice files**: an empty result means the photos have no `RunKey` (SaveFleetPhotos step 2.1 not done, or the app not re-published).

**Email sender:** this keeps sending from the flow owner's mailbox, as today. When IT grants Send As on the shared mailbox, switch **Send an email (V2)** to **Send an email from a shared mailbox (V2)**.

The app doesn't call this flow; the SharePoint trigger starts it. So there's nothing to add in Power Apps Studio for it.

---

## Step 3: Power Apps Studio

- [ ] **1.** **Open the app for editing:** Power Apps → **Apps** → the Fleet Checklist app → **Edit**.
- [ ] **2.** **Data sources:** left bar → **Data** (cylinder icon).

  - [ ] **1.** **+ Add data** → **SharePoint** → the Fleet Operations site. Tick **GF Fleet Checklist Defects**, **GF Fleet Trucks** and **GF Fleet Daily Reviews** → **Connect**.
  - [ ] **2.** For **Fleet Checklist**, **Run Sheets**, **Run Sheet Details** and the **Fleet Photos** library: **⋯** next to each → **Refresh**, so the app sees the new columns. If **Run Sheets** isn't refreshed, scrRunSheet shows "The specified column 'NoofInvoicePhotos' does not exist".
- [ ] **3.** **Flows:** left bar → **Power Automate** (flow icon).

  - [ ] **1.** **SaveFleetPhotos:** first make sure step 2.1 is done and saved (the flow has the `RunKey` and `StopKey` inputs). Then **⋯** → **Remove from app**, then **+ Add flow** → **SaveFleetPhotos**. This re-reads its two new inputs. If the app still has the old version, scrRunSheet shows "Invalid number of arguments: received 8, expected 5-6".

  The submission email flow isn't added to the app; SharePoint starts it.
- [ ] **4.** **Screens:** paste each one in this order. After each, check that the formula checker (the ⚠ icon at the top) shows no errors before going on.

  - [ ] **1.** `screens/scrPhotos.txt`
  - [ ] **2.** `screens/scrPreTrip.txt`
  - [ ] **3.** `screens/scrRunSheet.txt`
  - [ ] **4.** `screens/scrReview.txt`
  - [ ] **5.** `screens/scrHome.txt`
  - [ ] **6.** `screens/scrUsers.txt`

  **To paste a screen:**

  - [ ] **1.** Open the file in VS Code → **Ctrl+A**, **Ctrl+C**.
  - [ ] **2.** In Studio's **Tree view**, right-click the old screen → **Delete**.
  - [ ] **3.** Right-click any screen → **Paste**.
  - [ ] **4.** Rename it if Studio added a suffix, for example `scrPreTrip_1` → `scrPreTrip`.
  - [ ] **5.** If you'd rather keep the old screen as a fallback, rename it to `scrPreTrip_old` instead of deleting it, and delete it once the new one works.

  `scrPreTrip` is **generated** from `scripts/checklist_items.json`. If its paste fails, tell Claude the error so the generator `scripts/build_pretrip_screen.py` gets fixed. Don't edit the screen by hand.
- [ ] **5.** **Optional, to test in a browser:** **Settings** → **Updates** (or **General**, depending on the Studio version) → turn on **Enable SaveData, LoadData, ClearData on web player**. Without it, the draft and offline features just don't save in a browser; nothing breaks.
- [ ] **6.** **Save** (Ctrl+S), then **Publish** → **Publish this version**.
- [ ] **7.** **On your phone:** close the Power Apps app fully, reopen it and pull down on **Recent apps** to refresh before opening the app. If it says "Download couldn't finish", open the app once in the phone's browser to check the published version, then sign out of Power Apps and back in.

---

## Step 4: Test

- [ ] **1.** **Checklist, as a driver:**
  - [ ] Pages: Back and Next work, the progress bar moves, and Submit appears on the last page only.
  - [ ] The truck number is locked; Site is required.
  - [ ] Ticking **No** opens a comment box, and Submit stays blocked until it's filled.
  - [ ] The number of tyre photos matches the truck's **Number of tyres** (6 if the truck isn't in the list).
  - [ ] COF, blower and truck service dates show **Expired / Due within 30 days / OK** for a truck that has dates.
  - [ ] Close the app halfway, reopen it → Home offers **Carry on** → your answers are still there.
  - [ ] Submit, then check the **Fleet Checklist** row, one **GF Fleet Checklist Defects** row per No, and the photos in **Fleet Photos**.
- [ ] **2.** **Run sheet, as a driver, in airplane mode:**
  - [ ] Times are entered as HH : MM; Arrive time comes first and "Time left the premises" last.
  - [ ] Add stops with a number of invoices and take each invoice photo.
  - [ ] Turn signal back on → the photos upload → Submit → the trip and stops appear in SharePoint.
  - [ ] The submission email arrives with the invoice photos attached and a link to them in Fleet Photos.
- [ ] **3.** **As a reviewer:**
  - [ ] Sign off a checklist, including **Cabin tilt** and **Underneath greasing**. Open a second checklist for the same truck in the same week: it shows "… inspection conducted on {date} by {name}".
  - [ ] Verify a run sheet.
  - [ ] **Daily review** tab: give the test driver stars and a comment.
- [ ] **4.** **As that driver the next day:**
  - [ ] Home shows "Your daily review for …" until **Got it**.

---

## Step 5: Waiting on others

| From             | What                                                                                                                                       | Then                                                                                                                                                                                                                                                                   |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pawan**  | Approval of the wording: [Fleet Checklist - item wording for approval.docx](<Fleet%20Checklist%20-%20item%20wording%20for%20approval.docx>) | Update `proposedName` in `scripts/checklist_items.json` for any changes, run `py -3 -I scripts/build_pretrip_screen.py screens`, then run `create_checklist_v2_columns.js` with `MODE = 'rename'`. No app paste is needed unless items were added or removed |
| **Krish**  | The truck table (number, type, tyres, dates) and which items are Frozen-only                                                               | Import the table with `create_trucks_list.js` (1.3). Set `truckType` in `checklist_items.json`, regenerate, and paste `scrPreTrip` again                                                                                                                       |
| **Office** | Each truck's COF, blower and truck service dates                                                                                           | Typed straight into GF Fleet Trucks                                                                                                                                                                                                                                    |
| **Labels** | A photo of the COF and blower stickers, plus what your phone reads if they have a QR code or barcode                                       | Decides whether a "Scan" button can fill the dates (free) or would need AI Builder (premium)                                                                                                                                                                           |
| **IT**     | Send As on the shared mailbox                                                                                                              | Switch Run Sheet - Submission email to **Send an email from a shared mailbox (V2)**                                                                                                                                                                              |

## Where things are documented

| Topic                                | Document                                                                             |
| ------------------------------------ | ------------------------------------------------------------------------------------ |
| Lists, columns and flows (reference) | [PROJECT_HANDOVER.md](../PROJECT_HANDOVER.md) §4 and "Meeting changes (23 Nov 2026)" |
| Why things were decided              | [PROJECT_HISTORY.md](../PROJECT_HISTORY.md)                                           |
| Screen and naming rules              | [CLAUDE.md](../CLAUDE.md)                                                             |
| Roles and process                    | [README.md](../README.md)                                                             |
