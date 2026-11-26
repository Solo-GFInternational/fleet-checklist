# fleet-checklist — Project Guide

> Snapshot written 2026-11-25. Sections 1-6 are reference; section 7 (Open items) goes stale. The live status is the project owner's auto-updated `STATUS-fleet-checklist.md` (OneDrive > Claude-Status).

Remote: https://github.com/Solo-GFInternational/fleet-checklist · Written 25 Nov 2026.
Live status and recent activity: [STATUS-fleet-checklist.md](STATUS-fleet-checklist.md) (same folder as this guide).

## 1. Overview

A phone-first **Power Apps canvas app** that replaces the GF truck fleet's daily paper forms from SOP DC/16.0 (V007): the Fleet Pre-Trip Checklist, the Fitness for Driving driver declaration and the Vehicle Run Sheet. Drivers fill them in on their phone; team leaders, supervisors and fleet controllers review and sign off in the same app.

- **Tech stack:** Power Apps canvas app (phone layout), SharePoint Online lists on the **Fleet Operations** site, Power Automate cloud flows, Python 3 (standard library) and browser-console JavaScript setup scripts. An older Microsoft Forms + flows track still exists but is no longer the main path.
- **Main components:** `screens/` (one paste-in YAML/Power Fx file per screen), `scripts/` (SharePoint list/column/permission creators, screen and flow generators), `files/` (SOP, forms, wording docs, truck data, setup guide), `email-templates/`.
- **There is no `.msapp` or `pac` solution source in the repo.** The app lives in the Power Platform environment; the repo holds screen code you paste into Studio.
- **Current state:** Nov 2026 release (changes from the 23 Nov meeting with Pawan's team) is built on branch `meeting-changes-2026-11`, not yet merged or deployed; pilot not started. See STATUS for detail.

## 2. Where to read to understand the project

1. `STATUS-fleet-checklist.md` (project owner's OneDrive > Claude-Status folder) — current state, recent commits, open TODOs and blockers. **Regenerated automatically after every commit** by the repo's `.git/hooks/post-commit` hook (calls `~/.claude/status-hooks/update-status.sh`, detached; log in `~/.claude/status-hooks/logs/fleet-checklist.log`). The hook is local, not in git.
2. `README.md` — the business process (driver / office), list-per-record table, app roles vs business roles, contacts, milestone history.
3. `CLAUDE.md` — the coding rules: screen/control naming, internal column names, Yes/No checkbox pattern, brand palette, roles gating, offline run sheet design, checklist draft, registered-trucks-only. Read before touching any screen.
4. `files/Setup guide - Nov 2026 release.md` — tick-box, step-by-step deployment of the current release (SharePoint scripts → flows → Studio paste → phone tests → waiting on others).
5. `PROJECT_HANDOVER.md` — technical reference: §4 lists, flows (`SaveFleetPhotos` inputs §4.3, `SyncAppUser` §4.4, submission email §4.5), licensing §4.6; §7 gotchas. Sections 2–3 and 6 partly describe the earlier Forms track.
6. `PROJECT_HISTORY.md` — dated decision log (why Forms → Power Apps, why Run Sheet Details replaced Run Sheet Stops, why no invoice PDF, etc.).
7. `scripts/checklist_items.json` + `scripts/build_pretrip_screen.py` — single source for checklist items/order/photo rules and the generator for `screens/scrPreTrip.txt`.
8. `screens/scrHome.txt` (role lookup, truck scan, draft resume) → `scrPreTrip.txt` → `scrPhotos.txt` → `scrRunSheet.txt` (offline sync via `btnRunSync`) → `scrDecl.txt` → `scrReview.txt` → `scrUsers.txt`. `scrTest.txt` is a scratch screen.
9. `scripts/setup_app_permissions.js`, `create_*.js` — what the SharePoint lists, groups and permission levels look like; `scripts/build_submission_email_flow.py` — how the submission email flow package is built.
10. `files/` — `DC 16.0 DRIVER RESPONSIBILITIES & CUSTOMER SERVICE V007 16.07.2025.pdf` (source SOP), `Fitness for Driving Driver Declaration Form.pdf`, `Fleet Checklist - item wording for approval.docx/.md`, `Fleet Trucks.csv`, the `*.xlsx` list templates.
11. `../fleet-checklist-current` (sibling folder on the owner's PC, not in git) — **pre-git snapshot (≈19–20 Nov 2026)**, not a git repo. Its `CLAUDE.md` and `PROJECT_HISTORY.md` are identical to the repo's initial commit `585c2f7`; `PROJECT_HANDOVER.md` and `screens/scrHome.txt` differ slightly. Same `scripts/`, `screens/`, `email-templates/`, `files/` layout (fewer scripts, no scrUsers). Superseded by the repo — reference only, don't edit.
12. `../fleet-checklist-org` (sibling folder on the owner's PC, not in git) — oldest snapshot (19 Oct 2026), 3 files: the SOP PDF, `Fleet Pre-Trip Checklist - MS Forms import.docx` (original 20-question layout) and `Vehicle Run Sheet - MS Forms import.docx` (197 questions). Superseded (handover §7 "Related folder").
13. **Development history (git):**
    - Branches: `main` (only initial commit + README), `app-managed-access` (one commit, already contained in the next), `meeting-changes-2026-11` (current work, 26 commits ahead of main). Convention: one branch per change set off `main`; merge to `main` before deploying (setup guide Step 0).
    - `git log --oneline --graph --all` — overall shape.
    - `git log main..meeting-changes-2026-11 --oneline` — what the release adds.
    - `git log --follow -p -- scripts/checklist_items.json` — how checklist wording/order evolved.
    - `git log -p -- CLAUDE.md` — when each rule was added. Commit messages are plain English and descriptive.

## 3. Working on it

**Prerequisites**
- Windows laptop with Git, VS Code (optionally *Markdown All in One* for the setup guide tick boxes), Python 3 via the `py` launcher (standard library only — `pip`/`npm install` fail behind corporate SSL inspection).
- Microsoft 365 account with Power Apps and Power Automate (standard licences; no premium connectors are used), Edge or Chrome.
- Co-owner/edit rights on the Fleet Checklist app, the flows, and Owner on the Fleet Operations SharePoint site (see §5).
- Power Apps mobile app on a phone for testing offline run sheets and QR scanning.

**Edit and test a change**
1. Clone: `git clone https://github.com/Solo-GFInternational/fleet-checklist.git`, then `git checkout meeting-changes-2026-11` (or branch off it).
2. Edit screen code in `screens/scr<Name>.txt` following `CLAUDE.md`. For the checklist, edit `scripts/checklist_items.json` and regenerate: `py -3 -I scripts/build_pretrip_screen.py screens` — never hand-edit `scrPreTrip.txt`.
3. SharePoint changes: copy a `scripts/*.js` file into the browser console (F12) on the Fleet Operations site as a site Owner, run with `DRY_RUN = true` first, then `false` (setup guide "How to run a setup script"). Scripts are re-runnable.
4. Power Apps Studio → open the app → Edit → delete (or rename to `_old`) the old screen → paste the new one → fix the screen name suffix → check the formula checker shows no errors. Refresh data sources if columns changed; remove/re-add a flow if its trigger inputs changed.
5. Test in Studio preview (optionally enable *SaveData/LoadData on web player* in Settings), then on a phone after Publish — including airplane mode for the run sheet. Use the test-data scripts `create_test_checklist.js` / `create_test_runsheet.js` if needed.
6. Commit to the branch (the post-commit hook then refreshes STATUS). Python build scripts take an output folder as first argument (`files/` or `screens`).

## 4. Deployment & environments

- **Environments:** only one is evidenced — the live app, flows and lists in the Fleet Operations site/default environment. No dev/test environment, solution or ALM pipeline is documented — confirm with project owner.
- **How changes reach users:** paste screens into Studio → **Save** → **Publish this version**; users refresh *Recent apps* in the Power Apps mobile app. SharePoint scripts take effect immediately (run at a quiet time).
- **Current release steps** (all in `files/Setup guide - Nov 2026 release.md`): merge branch → run `create_checklist_v2_columns.js` (now `MODE = 'rename'`), `create_checklist_defects.js`, `create_trucks_list.js`, `create_runsheet_v2_columns.js`, `create_daily_reviews.js` → add `RunKey`/`StopKey` optional inputs to **SaveFleetPhotos** → build `Run Sheet - Submission email v2` with `py -3 -I scripts/build_submission_email_flow.py files "<exported flow zip>"`, import via *Import Package (Legacy)*, turn the **new flow on and the old one off** → in Studio add data sources (Defects, Trucks, Daily Reviews), refresh others, re-add SaveFleetPhotos, paste screens in the guide's order → publish → test.
- **Flows the app depends on:** `SaveFleetPhotos` (instant, called by app), `SyncAppUser` (instant, called by scrUsers), `Run Sheet - Submission email` (SharePoint-triggered, not in the app). Legacy Forms flows (Driver Declaration/Run Sheet/Pre-Trip → SharePoint) remain from the earlier track.
- **SharePoint (Fleet Operations site):** Fleet Checklist, GF Fleet Checklist Defects, Run Sheets, Run Sheet Details, Driver Declarations, GF Fleet Checklist App Users, GF Fleet Trucks, GF Fleet Daily Reviews, Fleet Photos library; groups Fleet App Drivers / Fleet App Reviewers.
- **Sharing/rollout:** share the app by name (not "Everyone") after reviewer roles are confirmed; pilot 1–2 trucks for a week. Sharing process beyond that — not documented, confirm with project owner.

## 5. Access & accounts needed

- **GitHub:** access to `Solo-GFInternational/fleet-checklist` (ask the project owner for access).
- **Power Apps:** co-owner of the Fleet Checklist canvas app (edit, publish, add flows/data sources).
- **Power Automate:** owner/co-owner of SaveFleetPhotos, SyncAppUser and Run Sheet - Submission email (a co-owner/service account is still to be added). SyncAppUser's owner must be able to manage SharePoint groups.
- **SharePoint:** site Owner on Fleet Operations (scripts break inheritance, create groups and permission levels).
- **App role:** a row in GF Fleet Checklist App Users with `AppRole = Admin` (added by an existing Admin on scrUsers).
- **Mailbox:** flow owner's Office 365 Outlook connection sends the submission email; shared-mailbox **Send As** pending from IT.
- **Licences:** Microsoft 365 for every user (drivers ideally Frontline F1/F3 — confirm with IT); no premium Power Platform licence needed today.
- **People:** Solomone Tuilagivou (owner/developer, Admin), Krish Kumar (fleet ops stakeholder), Pawan's team (wording approval), IT (licences, Send As, service account), office (truck due dates).

## 6. Conventions & gotchas

- **Internal vs display column names:** formulas, `Choices()` and `DataSourceInfo()` use internal names (`field_4`, `COFExpiry`); display names are just labels. Checklist wording changes are display-name renames via script, not app changes. Internal names are permanent — create short no-space names first (spaces become `_x0020_`).
- **Generated screen:** `scrPreTrip.txt` comes from `checklist_items.json`; edit the JSON or the generator's templates only.
- **Drivers are add-only:** driver-side code uses `Patch(..., Defaults(...))` only, never edits existing rows; run sheet writes go only through `btnRunSync`. SharePoint permissions are the real security, not hidden buttons.
- **Users only via scrUsers → SyncAppUser;** never Patch App Users from the app, never add app users to the site Members group.
- **Delegation / list size:** filter Run Sheet Details on the number column `RunSheetID`, not the lookup (only 500 rows search otherwise). Index Date/Truck/RunKey columns; Fleet Photos will pass 5,000 items.
- **Paste pitfalls:** formulas containing `: ` need block form `Prop: |-`; no `AccessibleLabel` on Classic/CheckBox (PA2108); use Classic/DropDown not ComboBox; never `Navigate` in `OnVisible`; control names prefixed (`btn`, `lbl`, `con`…), unique app-wide.
- **Flows:** after changing trigger inputs, remove and re-add the flow in Studio ("Invalid number of arguments"); optional inputs go in a record (`{file:…, text_4: RunKey, text_5: StopKey}`). Don't leave both old and v2 submission email flows on (double emails).
- **Breaking list inheritance** must copy existing permissions (the scripts do) — a bad break forced the Run Sheet Stops rebuild.
- **Secrets in exports:** `files/.gitignore` ignores `*.zip` because flow packages contain site URLs, list IDs and emails — keep it that way.
- **Offline** works only in the Power Apps mobile app and only for the run sheet; checklist and declaration need signal.

## 7. Open items

- Uncommitted work on `meeting-changes-2026-11` (registered-trucks-only, QR doc, rest-time panel, new truck files); `scripts/__pycache__/` should be git-ignored.
- Release not deployed: run the setup guide end to end, merge the branch to `main`, publish, then pilot.
- Flows depend on a single personal owner — add a co-owner / service account.
- Waiting on Krish (Frozen-only items, reviewer roles), office (truck due dates), IT (Send As on shared mailbox), Pawan (final wording sign-off before the rename).
- Backlog: Trade Issue and Fleet Checklist/MEX reporting emails, Team Leader run sheet approval columns, Phase 2 Driver Assessment.
- Full list: [STATUS-fleet-checklist.md](STATUS-fleet-checklist.md) "Next Steps & Open TODOs" and "Blockers".
