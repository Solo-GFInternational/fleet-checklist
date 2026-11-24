# Fleet Checklist – Accessory Checks columns

Requested by Krish Kumar (email "Re: Meeting Notes (16/11)", 16 Nov 2026). Used by the **Accessory Checks** section of `screens/scrPreTrip.txt`.

## Quick way: script

`scripts/create_accessory_columns.js` creates all 19 columns below (exact internal name and display name in one step) from the browser console, the same way as `scripts/list_columns.js`. Run it once with `DRY_RUN = true` to see the plan, then with `DRY_RUN = false`. It skips columns that already exist. Use the manual steps below if the script can't be run.

## How to create each column by hand (internal name matters)

SharePoint fixes a column's **internal name** from the name you type when you first create it. The app uses the internal name, so:

1. Open the **Fleet Checklist** list → **+ Add column** → pick the type below.
2. In **Name**, type the **Internal name** exactly (no spaces), e.g. `AccCOFExpiry`. Set the type options below. **Save**.
3. Click the new column header → **Column settings → Edit** → change **Name** to the **Display name** → **Save**.
   The display name is what drivers see in the app and what the photos are labelled with; the internal name stays the same.
4. Leave **Require that this column contains information** **off** for all of them (the app enforces it).

## Columns

| # | Internal name (type first) | Display name (rename to) | Type | Options |
| -- | -- | -- | -- | -- |
| 1 | `AccCOFExpiry` | COF Expiry Date | Date and time | Include time: **No** |
| 2 | `AccBlowerServiceDue` | Blower Service Due Date | Date and time | Include time: **No** |
| 3 | `AccTruckServiceDue` | Truck Service Due Date | Date and time | Include time: **No** |
| 4 | `AccSpareTyre` | Spare Tyre Availability | Choice | Choices: `Yes`, `No` · Default: none · Single select |
| 5 | `AccTyreCondition` | Tyre Condition | Choice | Yes / No, as above |
| 6 | `AccCabinClean` | Cabin Cleanliness | Choice | Yes / No |
| 7 | `AccFireExtinguisher` | Fire Extinguisher Mounted and Serviceable | Choice | Yes / No |
| 8 | `AccFirstAidKit` | First Aid Kit Available | Choice | Yes / No |
| 9 | `AccTrafficCones` | Traffic Cones Available | Choice | Yes / No |
| 10 | `AccFuelCard` | Fuel Card Available | Choice | Yes / No |
| 11 | `AccPlugWire` | Plug Wire Available | Choice | Yes / No |
| 12 | `AccMats` | Mats Available | Choice | Yes / No |
| 13 | `AccEngJack` | Engraved Jack Available | Choice | Yes / No |
| 14 | `AccEngWheelBrace` | Engraved Wheel Brace Available | Choice | Yes / No |
| 15 | `AccEngPipe` | Engraved Pipe Available | Choice | Yes / No |
| 16 | `AccEngTyreWinder` | Engraved Spare Tyre Winder Available | Choice | Yes / No |
| 17 | `AccEngTrolley` | Engraved Trolley Available | Choice | Yes / No |
| 18 | `AccTruckFloor` | Truck Floor Condition | Choice | Yes / No |
| 19 | `AccComments` | Accessory Checks – comments | Multiple lines of text | Plain text |

Choice columns: type `Yes` and `No` on separate lines, **Default value: (none)**, **Allow multiple selections: No**, **Can add values manually: No**. Spelling and capitals must be exactly `Yes` / `No` (the app writes those words).

## Photos

No SharePoint columns are needed for the photos. Each item's photo is uploaded by the existing **SaveFleetPhotos** flow, the same way as the odometer photo, with PhotoType = `Accessory`, Item = the column's display name, and RecordID = the checklist row ID.

## Check

Run `scripts/list_columns.js` with `LISTS = ['Fleet Checklist']` and confirm the 19 internal names above appear exactly.
