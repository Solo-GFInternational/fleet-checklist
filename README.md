# GF Fleet Checklist

A phone-first app that replaces the paper forms the truck fleet fills in every day. Drivers complete their pre-trip vehicle checks, fitness-for-driving declaration and delivery run sheet on their phone. Supervisors and team leaders then review and sign them off in the same app.

The paper forms come from SOP **DC/16.0 Driver Responsibilities & Customer Service (V007)**:

| Paper form | SOP source | Completed |
| --- | --- | --- |
| Fleet Pre-Trip Checklist | Appendix III | Before a vehicle is started, once per truck per day |
| Fitness for Driving – Driver Declaration | Separate paper form | By each driver at the start of a shift |
| Vehicle Run Sheet | Appendix II | Once per truck run, with a row per delivery stop |

---

## Tech stack

| Layer | Technology |
| --- | --- |
| Front end | **Microsoft Power Apps** canvas app (phone layout), written as paste-in YAML / Power Fx screen files in [screens/](screens/) |
| Data | **SharePoint Online lists** on the Fleet Operations site |
| Automation | **Power Automate** cloud flows (for example `SaveFleetPhoto`, which saves the checklist photos to a SharePoint library) |
| Offline | Power Apps `SaveData` / `LoadData` on the device (run sheet only, Power Apps mobile app) |
| Access control | SharePoint list **GF Fleet Checklist App Users** plus SharePoint list permissions |
| Build and setup scripts | **Python 3** (standard library only) for generating the Forms import files and list templates. **JavaScript** run in the browser console on the SharePoint site to create columns, lists and test data |
| Notifications | HTML email templates for Outlook "Send an email (V2)" in [email-templates/](email-templates/) (on hold, see History) |
| Earlier track | **Microsoft Forms** (Quick Import) + Power Automate flows into the same lists. Still in place, no longer the main path |

---

## Repository layout

| Folder | Contents |
| --- | --- |
| [screens/](screens/) | One file per Power Apps screen (`scr<Name>.txt`), pasted into Power Apps Studio |
| [scripts/](scripts/) | Scripts that build or set up parts of the system |
| [files/](files/) | Source and reference documents: the SOP, paper forms, Forms import files, list templates, test-data generator |
| [email-templates/](email-templates/) | HTML email bodies for the flows (`preview.html` shows them all) |
| [CLAUDE.md](CLAUDE.md) | Project conventions: naming, layout, brand palette, roles, offline rules |
| [PROJECT_HANDOVER.md](PROJECT_HANDOVER.md) | Detailed technical handover |
| [PROJECT_HISTORY.md](PROJECT_HISTORY.md) | Day-by-day decision log |

### Screens

| Screen | Purpose | Who |
| --- | --- | --- |
| `scrHome` | Truck scan or entry, role-based menu, offline banners | Everyone registered |
| `scrPreTrip` | Fleet pre-trip checklist: Yes/No with comments, sections from Licence and Odometer to Truck Profiles, photos. Also the manager's approval view and the weekly reviewer-only checks. **Generated** from `scripts/checklist_items.json` by `scripts/build_pretrip_screen.py` | Driver, then Reviewer |
| `scrPhotos` | Camera for checklist photos (odometer, items, tyres, profiles, accident, defects) | Driver |
| `scrRunSheet` | Trip details, unlimited delivery stops with invoice photos, return to CD. Works offline | Driver |
| `scrDecl` | Fitness for Driving declaration (14 statements) | Driver |
| `scrReview` | Review and sign-off of checklists, run sheets and declarations, plus the driver's **Daily review** (stars) | Reviewer, Admin |
| `scrUsers` | Manage users: add a person, change their role, remove access (calls the `SyncAppUser` flow) | Admin |
| `scrTest` | Scratch screen for testing controls | Developer |

---

## Process

### 1. Start of shift: driver

1. Open the app and scan or enter the truck number on **Home**.
2. Complete the **Fitness for Driving declaration**. Each statement is a checkbox. Any unticked statement makes Comments required and tells the driver to contact their supervisor.
3. Complete the **Pre-Trip Checklist**, in order: Licence and Odometer, Cabin, Electrical, Tyres, Leaks and Fluid Levels, then the rest. Each item says what the driver should see (for example "Battery water at top mark"), with a **Yes / No**. A **No** needs a comment. The truck number is locked to the truck chosen on Home, and Site is required.
4. Take the required **photos**: odometer, accessory items, one per tyre, net/gross weight plate, four truck profiles (Front, Rear, Left, Right), and accident photos if there's new damage. Submit stays locked until everything is answered and photographed. Photos upload through the `SaveFleetPhoto` flow after the checklist is saved.
5. If they were reviewed yesterday, Home shows their **Daily review** (stars and comment) until they tap "Got it".

### 2. During the run: driver

1. Open the **Run Sheet**. **Trip** tab: date, truck, partner, area, number of invoices, start mileage, actual departure time. Times are typed as HH : MM.
2. **Stops** tab: add a row per delivery stop (arrival time, destination, cartons, number of invoices with a photo of each, truck temperature, operation start and finish, HSEQ comments, time left the premises). Invoice photos are taken with the in-app camera and upload whenever there's signal. There is no limit on stops; a run is typically around 70.
3. **Return to CD** tab: time returned, end mileage, balance invoice, temperatures, quantity on balance delivery, invoice balanced with cashier. Then submit.
4. Without signal, everything is saved on the phone. **Upload** (or the next save once there is signal) sends the trip, then its stops, then the submission.

The run sheet stays on the phone until the driver submits it. Then the trip and its stops are sent to SharePoint as new rows. Drivers can only add records, never change them, so a sent stop can't be edited in the app. Run sheet status: **Open** (submitted, waiting for the team leader) → **Closed** (verified).

### 3. Review and sign-off: office

On **Review**, each tab has a *Waiting* / *All* filter:

- **Checklists**: the Fleet Controller / Site Engineer / Manager sets **Approval for Delivery** and **Send for Repairs**.
- **Run sheets**: the Team Leader checks the trip and its stops (temperatures above −15 °C or unloading over 15 minutes show in red) and selects **Verify run sheet**.
- **Declarations**: the Supervisor follows up any "No" answer (shown in red) and selects **Sign off**.
- **Daily review**: pick a date, then give each driver who submitted anything that day 1–5 stars and an optional comment.

When a reviewer opens a checklist, they also answer the weekly **Cabin tilting** and **Underneath greasing** checks. If that truck was already done this week, the app shows when and by whom instead.

### 4. Data

Everything is stored in SharePoint lists on the Fleet Operations site:

| List | One row per |
| --- | --- |
| Fleet Checklist | Pre-trip checklist |
| Run Sheets | Trip |
| Run Sheet Details | Delivery stop (linked by `RunSheetID`) |
| Driver Declarations | Declaration |
| GF Fleet Checklist App Users | App user and role |
| GF Fleet Trucks | Truck (type Ambient/Frozen, number of tyres) |
| GF Fleet Daily Reviews | Driver's star score for a day |
| GF Fleet Checklist Defects | Checklist item answered No, with its comment (Open/Fixed) |
| Photo library | Checklist and invoice photo |

---

## Required roles

### App roles

Set in the **GF Fleet Checklist App Users** list (Name, `UserEmail` in lower case, `AppRole`, `ActiveYN`). Roles stack: a Reviewer can do everything a Driver can, and an Admin everything a Reviewer can. Anyone not in the list, or marked inactive, gets role **None** and cannot use the app.

| App role | Can do |
| --- | --- |
| **Driver** | Declaration, pre-trip checklist and photos, run sheet |
| **Reviewer** | Everything a Driver can, plus the Review screen: approve checklists, verify run sheets, sign off declarations |
| **Admin** | Everything a Reviewer can. Admins also own the app and manage users on the **Manage users** screen |

Hiding buttons in the app is not security. **SharePoint list permissions are the real access boundary.**

- App users get list access through two SharePoint groups: **Fleet App Drivers** (role Driver) and **Fleet App Reviewers** (Reviewer and Admin). The `SyncAppUser` flow adds and removes people when an Admin uses the Manage users screen. No email is sent. Don't add app users to the site's Members group.
- The four record lists (Fleet Checklist, Run Sheets, Run Sheet Details, Driver Declarations) have their own permissions, set up by `scripts/setup_app_permissions.js`. Existing permissions were copied when they stopped inheriting, so the flows and site owners keep access. Drivers can **add** records but not edit or delete them. They can see only the records they created, because SharePoint won't allow adding without some view access, and item-level permissions limit it to their own. Reviewers (Edit + *Override List Behaviors*) see and sign off everything.
- The App Users list gives both groups Read. Only the flow writes to it.
- The photo library is written by the `SaveFleetPhoto` flow, so app users don't need access to it.

### Business roles

| Business role | Responsibility | App role |
| --- | --- | --- |
| Truck Driver | Fills in the declaration, checklist and run sheet | Driver |
| Team Leader | Verifies submitted run sheets | Reviewer |
| Supervisor | Signs off declarations and follows up any "No" | Reviewer |
| Fleet Controller / Site Engineer / Manager | Approves vehicles for delivery or sends them for repairs | Reviewer |
| Project owner / app administrator | Owns the app, lists and flows; manages users | Admin |

### Platform requirements

- A **Microsoft 365 account** for every user, and the app shared with them by name (not "Everyone").
- The **Power Apps mobile app** for offline run sheets. It needs one online launch first.
- Flows need a **co-owner**, ideally a service account, so they survive staff changes.
- Email alerts from the shared mailbox need **Send As** permission from IT.

---

## Contact points

| Contact | Role on the project |
| --- | --- |
| **Solomone Tuilagivou** | Project owner and developer: app, lists, flows, scripts. App Admin |
| **Krish Kumar** | Business stakeholder for fleet operations: requirements (accessory checks, reporting emails) and confirmation of reviewer roles |
| Reviewers (five recipients of the 16 Nov 2026 meeting notes) | Initial Reviewer users, roles to be confirmed with Krish |
| IT | Microsoft 365 licences, shared-mailbox Send As, service account |

---

## History

| Date (2026) | Milestone |
| --- | --- |
| Mid-Oct | Project started: the Pre-Trip Checklist and Vehicle Run Sheet digitised as **Microsoft Forms**, generated by `build_forms.py` for Forms Quick Import |
| 21 Oct | Fitness for Driving declaration added. **Power Apps + SharePoint** chosen as the target; Fleet Operations site and first lists created from `build_lists.py` templates |
| 21–23 Oct | Power Automate flows built from Forms into SharePoint: declarations (working), run sheet with 17 stop blocks, pre-trip fully mapped. Offline use requested by the business |
| 23 Oct | Email alerts put on hold: no Send As on the shared mailbox. Teams posts are the fallback |
| 26 Oct | Run Sheet flow confirmed working end to end |
| 2 Nov | Run Sheet Stops list replaced by **Run Sheet Details** after a permissions issue; flow rebuilt. Test-data generator added |
| Mid-Nov | Work moved to the **Power Apps canvas app** as the go-live path. Screens kept as paste-in files in `screens/` with a shared GF brand look |
| 16–18 Nov | Accessory checks with per-item photos (Krish Kumar's request) and Next Service Due added. Run sheet rebuilt as one offline-capable screen with unlimited stops. Delegation fix (`RunSheetID`) |
| 19 Nov | Declaration screen, Review / sign-off screen and checkbox answers. Role-based access through the App Users list |
| 20 Nov | Project put under git and published to GitHub |
| 23 Nov | App-managed user access; drivers add-only. Meeting with Pawan's team: checklist reordered with Yes/No and comments, new photo items, Trucks list, weekly reviewer checks, run sheet invoice photos and HH : MM times, Daily review stars |

### Next steps

1. Run the new setup scripts, add the new lists as data sources, update `SaveFleetPhoto`, paste the screens, and test on a phone (including airplane mode for the run sheet).
2. Build the `RunSheetSubmitted` flow (invoice PDF email).
3. Send the checklist wording to Pawan for approval; get the truck table from Krish and samples of the COF and blower labels.
4. Confirm reviewer roles with Krish, then share and publish the app.
5. Outstanding reporting emails: Trade Issue, Fleet Checklist export to Excel/MEX.
6. Phase 2: monthly Driver Assessment with an Assessor role.
7. Pilot with one or two trucks for a week, then roll out.

See [PROJECT_HISTORY.md](PROJECT_HISTORY.md) for the full log and [PROJECT_HANDOVER.md](PROJECT_HANDOVER.md) for technical detail.
