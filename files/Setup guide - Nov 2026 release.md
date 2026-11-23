# Setup guide: Nov 2026 release

Step-by-step setup for everything built after the 23 Nov 2026 meeting with Pawan's team:
- **Checklist:** the new checklist with Yes/No answers and comments, the defects list, the Trucks list, the draft saved on the phone, and one section per page.
- **Run sheet:** invoice photos and the invoice PDF email.
- **Review:** the Daily review.

Work through the steps in order. Each step links to where its background lives, but everything you need to do is in this guide.

| Step | Where | Who |
| --- | --- | --- |
| 0. Before you start | — | You |
| 1. SharePoint | Browser console on the Fleet Operations site | Site owner |
| 2. Power Automate | Power Automate | Flow owner |
| 3. Power Apps Studio | Power Apps | App owner |
| 4. Test | Phone and browser | You, plus a test driver and reviewer |
| 5. Waiting on others | — | Pawan, Krish, office |

---

## Step 0: Before you start

1. **Permissions setup has run.** `scripts/setup_app_permissions.js` must already have run on the site. It creates the groups **Fleet App Drivers** and **Fleet App Reviewers** and the permission levels **Fleet App Driver** and **Fleet App Reviewer**, which the new lists reuse.
   - If it hasn't, run it first, the same way as the scripts in Step 1.
   - Background: [PROJECT_HISTORY.md](../PROJECT_HISTORY.md) "Update 23 Nov 2026: app-managed access".
2. **The branch is merged.** Merge `meeting-changes-2026-11` into `main`, or work from that branch, so the files you paste are the latest.
3. **Pick a quiet time.** Pasting screens changes the live app only after **Publish**, but the SharePoint scripts change the lists straight away.

### How to run a setup script (same for every script in Step 1)

1. Open the **Fleet Operations** SharePoint site in **Edge or Chrome**, signed in as a **site Owner**. Any page of the site will do.
2. Press **F12** and open the **Console** tab.
3. Open the script file in VS Code, select everything (**Ctrl+A**) and copy it (**Ctrl+C**).
4. Leave `const DRY_RUN = true;` near the top for the first run.
5. Click in the console, paste (**Ctrl+V**) and press **Enter**. If the console refuses, type `allow pasting`, press **Enter**, then paste again.
6. Read what it prints between the `=====` lines. A dry run only lists what it **would** do.
7. If that looks right, change the line to `const DRY_RUN = false;`, paste the whole file again and press **Enter**.
8. Copy the output between the `=====` lines and keep it, for example in your notes.

What the output can tell you:

| Output | What it means | What to do |
| --- | --- | --- |
| `skip … (exists)` | Already done on an earlier run | Nothing. Every script can be run again safely |
| `SKIPPED … group or permission level missing` | `setup_app_permissions.js` hasn't run | Run it, then run this script again |
| `DO BY HAND …` | SharePoint wouldn't take the "own items only" setting from a script | Follow the List settings steps it prints |
| `FAILED …` | Something went wrong | Copy the whole output and look into it before going on |

---

## Step 1: SharePoint

Run these in order, each one dry run first.

### 1.1 Checklist columns: `scripts/create_checklist_v2_columns.js`

- Keep `const MODE = 'create';`.
- **What it does:**
  - Adds the new Yes/No columns to **Fleet Checklist**: `LicenceValid`, `CabGlassDriver`, `CabGlassPassenger`, `CabTilt`, `AccidentDamage`.
  - Indexes `field_1` (Truck No), which the weekly cabin tilt / greasing look-up needs.
- **Later:** once Pawan approves the wording, run it again with `MODE = 'rename'` (see Step 5).

### 1.2 Defects list: `scripts/create_checklist_defects.js`

- **List:** creates **GF Fleet Checklist Defects**, one row per checklist item answered No.
- **Columns:** Item (the wording), `ChecklistID`, `Truck`, `ItemField`, `Comment`.
- **Permissions:**
  - Drivers can add rows but not edit them, and see only their own.
  - Reviewers see and edit all rows.
  - Nobody in the app groups can delete.

### 1.3 Trucks list: `scripts/create_trucks_list.js`

- **List:** creates **GF Fleet Trucks**, one row per truck.
- **Columns:**
  - Title: the truck number, as "FJ 101"
  - Truck type: Ambient or Frozen
  - Number of tyres
  - Active
  - COF expiry, Blower service due, Truck service due
- **Permissions:** Drivers can read; Reviewers can edit, so the office keeps the dates current.
- **Optional import:** paste Krish's truck table between the backticks of `const CSV_TEXT = \`` … `\`;`, in this format. The three date columns are optional. Dates can be `yyyy-mm-dd` or `dd/mm/yyyy`.
  ```
  Truck,Type,Tyres,COF,BlowerService,TruckService
  FJ101,Frozen,6,2027-03-31,2027-01-15,2026-12-20
  ```
  Trucks already in the list are skipped, so you can also add trucks by hand later.
- **If you ran an earlier version** that created `LastOdometer` / `LastOdometerDate`, delete those two columns: List settings → click the column → **Delete**. The app no longer uses them.

### 1.4 Run sheet columns: `scripts/create_runsheet_v2_columns.js`

- Adds `NoofInvoices` ("No of invoices") to **Run Sheet Details**.
- Adds `RunKey` and `StopKey` (text) to the **Fleet Photos** library.

### 1.5 Daily review list: `scripts/create_daily_reviews.js`

- **List:** creates **GF Fleet Daily Reviews**.
- **Columns:** Driver, `DriverEmail`, `ReviewDate`, `Stars` (1–5), `Comment`, `ReviewerName`, Active.
- **Permissions:** Reviewers add and edit; Drivers read.

### 1.6 By hand in SharePoint

1. **Index `RunKey` on the Fleet Photos library.** The invoice PDF flow searches on it, and the library will pass 5,000 files.
   - Open the library → **⚙ Settings** → **Library settings** → **More library settings** → **Indexed columns** → **Create a new index**.
   - **Primary column: RunKey** → **Create**.
2. **Create a folder for the PDFs.** In the Fleet Photos library: **+ New → Folder** → `Run sheet PDFs` → **Create**.
3. **Ask the office to fill in each truck's dates** in GF Fleet Trucks: COF expiry, Blower service due, Truck service due. The checklist shows them as Expired / Due within 30 days / OK. When a truck has no date, the driver types it and takes a photo instead.

---

## Step 2: Power Automate

### 2.1 SaveFleetPhoto: add two inputs

The run sheet now uploads invoice photos through this flow, tagged with the run and the stop. Background: [PROJECT_HANDOVER.md §4.3](../PROJECT_HANDOVER.md#43-power-apps-flow-savefleetphoto).

1. Power Automate → **My flows** → **SaveFleetPhoto** → **Edit**.
2. Click the trigger card, **When Power Apps calls a flow (V2)**.
3. **+ Add an input** → **Text** → name it `RunKey`. Then **⋯** on that input → **Make the field optional**.
4. **+ Add an input** → **Text** → name it `StopKey` → **⋯** → **Make the field optional**.

   They must come **after** the six existing inputs, in this order.
5. Open the **Update file properties** action. Fill **Run key** with `RunKey` and **Stop key** with `StopKey`, from the trigger's dynamic content. Tokens from the trigger are fine here; it's the SharePoint tokens that add unwanted loops.
6. **Save**.

The checklist's existing six-input call keeps working, because the new inputs are optional. You'll remove and re-add the flow in the app in Step 3.

### 2.2 RunSheetSubmitted: build the invoice PDF email flow

The app calls this once a submitted run sheet, every stop and every invoice photo are in SharePoint.

What the flow does:
1. Answers the app straight away, so the driver isn't kept waiting.
2. Builds one PDF of the run's invoice photos and saves it next to the photos.
3. Emails it.
4. Marks the run as emailed.

Background: [PROJECT_HANDOVER.md §4.5](../PROJECT_HANDOVER.md#45-power-apps-flow-runsheetsubmitted-designed-23-nov-2026-not-built-yet). You already did the "Before you start" steps in 1.6.

**How to read the steps below**
- **Click** means a button or menu in Power Automate.
- `Code like this` is text you type or paste.
- An **expression** is entered by clicking the field → the **fx** (Expression) tab → pasting → **Add**. Never pick the SharePoint "dynamic content" tokens for these. They add automatic *Apply to each* loops (see the 23 Nov lessons in [PROJECT_HISTORY.md](../PROJECT_HISTORY.md)).
- **Rename every action straight after adding it**, exactly as written: click **⋯** on the action → **Rename**. The expressions refer to actions by these names.
- Wherever a step asks for **Site Address**, pick the Fleet Operations site from the drop-down.

#### Before you start (one-off; done in 1.6 and 1.4)

1. **Index `RunKey` in the Fleet Photos library.** The library will pass 5,000 files, and the filter in step 9 fails on columns that aren't indexed.
   - Open the library → **⚙ Settings** (top right) → **Library settings** → **More library settings** → **Indexed columns** → **Create a new index**.
   - **Primary column: RunKey** → **Create**.
2. **Agree who receives the email** (for example the Team Leaders or a shared address) with Krish.
3. **Run `scripts/create_runsheet_v2_columns.js` first** if you haven't already. It creates `RunKey` and `StopKey`.

#### Create the flow

1. Open Power Automate → **My flows** (left) → **+ New flow** → **Instant cloud flow**.
2. **Flow name:** `RunSheetSubmitted`. Choose the trigger **When Power Apps calls a flow (V2)** → **Create**.
3. **Trigger inputs:** click the trigger card → **+ Add an input** → **Text**. Name it `RunSheetID`. Again **+ Add an input** → **Text**, name it `RunKey`. The order matters:
   - `RunSheetID` = `triggerBody()['text']`
   - `RunKey` = `triggerBody()['text_1']`

#### Variables (they must sit at the top level, directly under the trigger)

4. **+** under the trigger → **Add an action** → search **Initialize variable**. Add it four times, renaming each one to match its Name:

   | Rename to | Name | Type | Value |
   | --- | --- | --- | --- |
   | `Init seen` | `seen` | Array | `[]` |
   | `Init keep` | `keep` | Array | `[]` |
   | `Init cartons` | `cartons` | Float | `0` |
   | `Init flagged` | `flagged` | String | (leave empty) |

   Add a fifth, `Init html`: Name `html`, Type **String**, Value:
   ```
   <html><body style="font-family:Arial,sans-serif">
   ```

#### Guard: never send twice

5. **+** → **SharePoint – Get item**. Rename it `Get run`.
   - **Site Address:** Fleet Operations
   - **List Name:** Run Sheets
   - **Id:** expression `int(triggerBody()['text'])`
6. **+** → **Condition**. Rename it `Already sent`.
   - Left box, expression: `outputs('Get_run')?['body/SubmissionEmailSent']`
   - Operator: **is equal to**
   - Right box, expression: `true`
7. In **True**, add two actions:
   1. **Respond to a PowerApp or flow**. Click **+ Add an output** → **Yes/No**, name `ok`, value expression `true`. Then **+ Add an output** → **Text**, name `message`, value `Already emailed`.
   2. **Control – Terminate**, Status **Succeeded**.

   Leave **False** empty.

#### Answer the app now

8. Below the condition (not inside it), add **Respond to a PowerApp or flow**. Rename it `Respond to app`.
   - `ok` (Yes/No) = expression `true`
   - `message` (Text) = `Sending`
   - The two outputs must have **the same names and types** as the ones in step 7. Copy that action with **⋯ → Copy to my clipboard**, then paste it here.

#### Build and send (everything inside one Scope, so failures can be caught)

9. **+** → **Control – Scope**. Rename it `Build and send`. Add every action below **inside** this scope.
   1. **SharePoint – Get items.** Rename it `Get stops`.
      - **List Name:** Run Sheet Details
      - **Show advanced options → Filter Query:** `RunSheetID eq ` then the expression `triggerBody()['text']`
      - **Order By:** `StopOrder`
      - **Top Count:** `5000`
   2. **SharePoint – Get files (properties only).** Rename it `Get invoice files`.
      - **Library Name:** Fleet Photos
      - **Filter Query:** `RunKey eq '` then the expression `triggerBody()['text_1']` then `'`, so it reads `RunKey eq '<key>'`
      - **Order By:** `Created desc`
      - **Top Count:** `500`
   3. **Control – Apply to each.** Rename it `For each file`.
      - **Select an output:** expression `body('Get_invoice_files')?['value']`
      - **⋯ → Settings → Concurrency control: On, Degree of parallelism: 1 → Done**
      - Inside it, add a **Condition**, renamed `New slot`. Left box expression: `contains(variables('seen'), concat(items('For_each_file')?['StopKey'], '|', items('For_each_file')?['Item']))`. Operator **is equal to**. Right box expression: `false`.
      - In **True**, add two actions:
        1. **Append to array variable**: `seen`, value expression `concat(items('For_each_file')?['StopKey'], '|', items('For_each_file')?['Item'])`.
        2. **Append to array variable**: `keep`, value expression `items('For_each_file')`.

      Newest files come first, so a retaken invoice photo wins and the older copy is skipped.
   4. **Control – Apply to each.** Rename it `For each stop`.
      - **Select an output:** expression `body('Get_stops')?['value']`
      - Concurrency **On, 1**, as above.
      - Inside it:
        1. **Increment variable:** `cartons` by expression `float(coalesce(items('For_each_stop')?['NoofCtns'], 0))`
        2. **Condition**, renamed `Flagged`. Click **+ Add → Add row**, then switch the group to **Or**:
           - Row 1: expression `float(coalesce(items('For_each_stop')?['TruckTemp'], -99))` **is greater than** `-15`.
           - Row 2: expression `float(coalesce(items('For_each_stop')?['Duration'], 0))` **is greater than** `15`.
        3. In **True**, add **Append to string variable**: `flagged`, value expression:
           ```
           concat('<tr><td style="padding:7px 12px; border-bottom:1px solid #E5E8EB; color:#5F6B76;">', items('For_each_stop')?['StopOrder'], '</td><td style="padding:7px 12px; border-bottom:1px solid #E5E8EB;">', items('For_each_stop')?['Title'], '</td><td style="padding:7px 12px; border-bottom:1px solid #E5E8EB; text-align:right;"><span style="display:inline-block; padding:2px 8px; border-radius:10px; color:#1F2933; font-weight:600; font-size:12px; background:#F8D000;">', if(greater(float(coalesce(items('For_each_stop')?['TruckTemp'], -99)), -15), concat('Temp ', items('For_each_stop')?['TruckTemp'], ' °C '), ''), if(greater(float(coalesce(items('For_each_stop')?['Duration'], 0)), 15), concat('Unload ', items('For_each_stop')?['Duration'], ' min'), ''), '</span></td></tr>')
           ```
   5. **Append to string variable**: `html`, value expression:
      ```
      concat('<h2 style="color:#007070">Run sheet invoices: ', outputs('Get_run')?['body/Title'], ' · ', formatDateTime(outputs('Get_run')?['body/RunDate'], 'dd MMM yyyy'), '</h2><p>Driver: ', coalesce(outputs('Get_run')?['body/DriverName'], ''), ' · Area: ', coalesce(outputs('Get_run')?['body/Area'], ''), ' · Stops: ', length(body('Get_stops')?['value']), ' · Invoice photos: ', length(variables('keep')), '</p>')
      ```
   6. **Control – Apply to each.** Rename it `For each invoice`.
      - **Select an output:** expression `reverse(variables('keep'))`. This puts them oldest first, which is roughly stop order.
      - Concurrency **On, 1**.
      - Inside it:
        1. **SharePoint – Get file content**, renamed `Get invoice content`. **File Identifier:** expression `items('For_each_invoice')?['{Identifier}']`.
        2. **Append to string variable**: `html`, value expression:
           ```
           concat('<div style="page-break-before:always"><p style="font-size:14px; color:#1F2933">', items('For_each_invoice')?['Item'], '</p><img src="data:image/jpeg;base64,', body('Get_invoice_content')?['$content'], '" style="width:100%"></div>')
           ```
   7. **Append to string variable**: `html`, value `</body></html>`
   8. **OneDrive for Business – Create file.** Rename it `Create HTML`.
      - **Folder Path:** `/Run sheet PDFs`. Create that folder in your OneDrive first.
      - **File Name:** expression `concat('Run_', triggerBody()['text'], '.html')`
      - **File Content:** expression `variables('html')`
   9. **OneDrive for Business – Convert file.** Rename it `Convert to PDF`.
      - **File:** expression `outputs('Create_HTML')?['body/Id']`
      - **Target type:** PDF
   10. **SharePoint – Create file.** Rename it `Save PDF`.
       - **Folder Path:** the Fleet Photos library, folder `Run sheet PDFs`. Make that folder in the library first: **+ New → Folder**.
       - **File Name:** expression `concat('RunSheet_', replace(outputs('Get_run')?['body/Title'], ' ', ''), '_', formatDateTime(outputs('Get_run')?['body/RunDate'], 'yyyyMMdd'), '_', triggerBody()['text'], '.pdf')`
       - **File Content:** expression `body('Convert_to_PDF')`
   11. **Data Operation – Compose.** Rename it `Template`. Paste the whole of [email-templates/run-sheet-submitted.html](../email-templates/run-sheet-submitted.html) into **Inputs**.
   12. **Data Operation – Compose.** Rename it `Email body`. **Inputs:** expression:
       ```
       replace(replace(replace(replace(replace(replace(replace(replace(replace(outputs('Template'), 'TRUCK', coalesce(outputs('Get_run')?['body/Title'], '')), 'DRIVER', coalesce(outputs('Get_run')?['body/DriverName'], '')), 'RUN_DATE', formatDateTime(outputs('Get_run')?['body/RunDate'], 'dd MMM yyyy')), 'AREA', coalesce(outputs('Get_run')?['body/Area'], '')), 'STOPS_COUNT', string(length(body('Get_stops')?['value']))), 'CARTONS', string(variables('cartons'))), 'INVOICE_COUNT', string(length(variables('keep')))), 'FLAGGED_STOPS', if(empty(variables('flagged')), '<tr><td colspan="3" style="padding:7px 12px; border-bottom:1px solid #E5E8EB; color:#5F6B76;">None</td></tr>', variables('flagged'))), 'LIST_LINK', concat('<your Fleet Operations site address>', outputs('Save_PDF')?['body/Path']))
       ```
       Type your Fleet Operations site address in place of `<your Fleet Operations site address>`. It goes in the flow only; don't save it in this repo. The button in the email then opens the saved PDF.
   13. **Condition.** Rename it `Small enough to attach`.
       - Left box, expression: `length(string(body('Convert_to_PDF')?['$content']))`
       - Operator: **is less than**
       - Right box: `26000000` (about 19 MB of PDF; Outlook rejects attachments much bigger than that)
   14. **In True:** **Office 365 Outlook – Send an email (V2).**
       - **To:** the agreed addresses
       - **Subject:** expression `concat('Run sheet submitted: ', outputs('Get_run')?['body/Title'], ' ', formatDateTime(outputs('Get_run')?['body/RunDate'], 'dd MMM yyyy'))`
       - **Body:** click **</>** (code view), then the expression `outputs('Email_body')`
       - **Show advanced options → Attachments → + Add new item:**
         - **Attachments Name:** expression `outputs('Save_PDF')?['body/Name']`
         - **Attachments Content:** expression `body('Convert_to_PDF')`
   15. **In False:** add the same **Send an email (V2)**, but with no attachment. The button in the email links to the saved PDF.
   16. **OneDrive for Business – Delete file**, after the condition, still inside the scope. **File:** expression `outputs('Create_HTML')?['body/Id']`.
   17. **SharePoint – Send an HTTP request to SharePoint.** Rename it `Mark email sent`.
       - **Method:** POST
       - **Uri:** `_api/web/lists/getbytitle('Run Sheets')/items(` then the expression `triggerBody()['text']` then `)`
       - **Headers** (four rows):

         | Key | Value |
         | --- | --- |
         | `Accept` | `application/json;odata=nometadata` |
         | `Content-Type` | `application/json;odata=nometadata` |
         | `IF-MATCH` | `*` |
         | `X-HTTP-Method` | `MERGE` |

       - **Body:** `{"SubmissionEmailSent": true}`

       This sets one column without having to resend the list's required columns, which **Update item** would demand.

#### Tell the owner if it fails

10. Below the scope (outside it), add **Office 365 Outlook – Send an email (V2).** Rename it `Tell owner it failed`.
    - **To:** your address
    - **Subject:** expression `concat('RunSheetSubmitted failed for run ', triggerBody()['text'])`
    - **Body:** the [flow-failure](../email-templates/flow-failure.html) template, or a short note with the run ID
    - Then **⋯ → Configure run after**: untick **is successful**, tick **has failed** and **has timed out** → **Done**.

#### Save, test, add to the app

11. **Save** (top right).
12. **Test → Manually → Test.** Enter the ID of a real submitted run and its LocalKey (the `RunKey` column on one of its photos in Fleet Photos) → **Run flow**. Then check:
    - The run history shows every step green.
    - The PDF is in Fleet Photos / Run sheet PDFs, with one page per invoice and readable images.
    - The email arrived.
    - The run's `SubmissionEmailSent` is now Yes.
    - Running the test a second time stops at "Already sent".
13. **Add it to the app:** Power Apps Studio → **Power Automate** pane (left) → **+ Add flow** → `RunSheetSubmitted`. Re-add it whenever the trigger inputs change.
14. **Connections:** a flow called from Power Apps runs with the flow owner's connections, like SaveFleetPhoto, so drivers don't need SharePoint, OneDrive or Outlook access of their own. Add a co-owner (**Details → Owners → Edit**) so the flow survives staff changes.

**If the PDF comes out with blank images,** OneDrive didn't render the embedded pictures. Check the HTML file in OneDrive before it's deleted (disable step 16 while testing). If the `<img>` tags have data, try smaller photos. If they're empty, check the **Get invoice content** output.

**Email sender:** until IT grants Send As on the shared mailbox, this sends from the flow owner's mailbox. A Teams post with the PDF (**Microsoft Teams – Post message in a chat or channel**, plus a link to the saved PDF) is the fallback.

---

## Step 3: Power Apps Studio

1. **Open the app for editing:** Power Apps → **Apps** → the Fleet Checklist app → **Edit**.
2. **Data sources:** left bar → **Data** (cylinder icon).
   1. **+ Add data** → **SharePoint** → the Fleet Operations site. Tick **GF Fleet Checklist Defects**, **GF Fleet Trucks** and **GF Fleet Daily Reviews** → **Connect**.
   2. For **Fleet Checklist**, **Run Sheet Details** and the **Fleet Photos** library: **⋯** next to each → **Refresh**, so the app sees the new columns.
3. **Flows:** left bar → **Power Automate** (flow icon).
   1. **SaveFleetPhoto:** **⋯** → **Remove from app**, then **+ Add flow** → **SaveFleetPhoto**. This re-reads its two new inputs.
   2. **+ Add flow** → **RunSheetSubmitted**.
4. **Screens:** paste each one in this order. After each, check that the formula checker (the ⚠ icon at the top) shows no errors before going on.
   1. `screens/scrPhotos.txt`
   2. `screens/scrPreTrip.txt`
   3. `screens/scrRunSheet.txt`
   4. `screens/scrReview.txt`
   5. `screens/scrHome.txt`
   6. `screens/scrUsers.txt`

   **To paste a screen:**
   1. Open the file in VS Code → **Ctrl+A**, **Ctrl+C**.
   2. In Studio's **Tree view**, right-click the old screen → **Delete**.
   3. Right-click any screen → **Paste**.
   4. Rename it if Studio added a suffix, for example `scrPreTrip_1` → `scrPreTrip`.
   5. If you'd rather keep the old screen as a fallback, rename it to `scrPreTrip_old` instead of deleting it, and delete it once the new one works.

   `scrPreTrip` is **generated** from `scripts/checklist_items.json`. If its paste fails, tell Claude the error so the generator `scripts/build_pretrip_screen.py` gets fixed. Don't edit the screen by hand.
5. **Optional, to test in a browser:** **Settings** → **Updates** (or **General**, depending on the Studio version) → turn on **Enable SaveData, LoadData, ClearData on web player**. Without it, the draft and offline features just don't save in a browser; nothing breaks.
6. **Save** (Ctrl+S), then **Publish** → **Publish this version**.
7. **On your phone:** close the Power Apps app fully, reopen it and pull down on **Recent apps** to refresh before opening the app. If it says "Download couldn't finish", open the app once in the phone's browser to check the published version, then sign out of Power Apps and back in.

---

## Step 4: Test

1. **Checklist, as a driver:**
   - [ ] Pages: Back and Next work, the progress bar moves, and Submit appears on the last page only.
   - [ ] The truck number is locked; Site is required.
   - [ ] Ticking **No** opens a comment box, and Submit stays blocked until it's filled.
   - [ ] The number of tyre photos matches the truck's **Number of tyres** (6 if the truck isn't in the list).
   - [ ] COF, blower and truck service dates show **Expired / Due within 30 days / OK** for a truck that has dates.
   - [ ] Close the app halfway, reopen it → Home offers **Carry on** → your answers are still there.
   - [ ] Submit, then check the **Fleet Checklist** row, one **GF Fleet Checklist Defects** row per No, and the photos in **Fleet Photos**.
2. **Run sheet, as a driver, in airplane mode:**
   - [ ] Times are entered as HH : MM; Arrive time comes first and "Time left the premises" last.
   - [ ] Add stops with a number of invoices and take each invoice photo.
   - [ ] Turn signal back on → the photos upload → Submit → the trip and stops appear in SharePoint.
   - [ ] The PDF is saved in Fleet Photos / Run sheet PDFs and the email arrives.
3. **As a reviewer:**
   - [ ] Sign off a checklist, including **Cabin tilt** and **Underneath greasing**. Open a second checklist for the same truck in the same week: it shows "… inspection conducted on {date} by {name}".
   - [ ] Verify a run sheet.
   - [ ] **Daily review** tab: give the test driver stars and a comment.
4. **As that driver the next day:**
   - [ ] Home shows "Your daily review for …" until **Got it**.

---

## Step 5: Waiting on others

| From | What | Then |
| --- | --- | --- |
| **Pawan** | Approval of the wording: [Fleet Checklist - item wording for approval.docx](Fleet%20Checklist%20-%20item%20wording%20for%20approval.docx) | Update `proposedName` in `scripts/checklist_items.json` for any changes, run `py -3 -I scripts/build_pretrip_screen.py screens`, then run `create_checklist_v2_columns.js` with `MODE = 'rename'`. No app paste is needed unless items were added or removed |
| **Krish** | The truck table (number, type, tyres, dates) and which items are Frozen-only | Import the table with `create_trucks_list.js` (1.3). Set `truckType` in `checklist_items.json`, regenerate, and paste `scrPreTrip` again |
| **Office** | Each truck's COF, blower and truck service dates | Typed straight into GF Fleet Trucks |
| **Labels** | A photo of the COF and blower stickers, plus what your phone reads if they have a QR code or barcode | Decides whether a "Scan" button can fill the dates (free) or would need AI Builder (premium) |
| **IT** | Send As on the shared mailbox | Switch RunSheetSubmitted's emails to the shared mailbox |

## Where things are documented

| Topic | Document |
| --- | --- |
| Lists, columns and flows (reference) | [PROJECT_HANDOVER.md](../PROJECT_HANDOVER.md) §4 and "Meeting changes (23 Nov 2026)" |
| Why things were decided | [PROJECT_HISTORY.md](../PROJECT_HISTORY.md) |
| Screen and naming rules | [CLAUDE.md](../CLAUDE.md) |
| Roles and process | [README.md](../README.md) |
