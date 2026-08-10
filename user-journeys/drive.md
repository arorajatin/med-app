# Drive Journey

## Goal

Browse upload-complete reports through dynamic person, month, and trusted-condition views.

## Journey

1. The account manager opens Drive.
2. If `self` is the only profile, Drive selects it automatically.
3. If multiple profiles exist, the account manager first selects one person.
4. Within that person, the account manager chooses:
   - organize by month; or
   - organize by condition.
5. Opening a group lists reports sorted by trusted report date descending.
6. Opening a report leads to its detail, observations, review, download, rename, and delete actions as available.

## Dynamic groups

- Month groups use confirmed, edited, or user-entered report date.
- Reports without a trusted report date appear under `Undated`.
- Condition groups use only report-linked user-attested conditions or confirmed or edited `documented_condition_candidate` values.
- Pending or ignored documented-condition candidates never create a group.
- Medications, dosages, lab values, ranges, flags, symptoms, and general medical associations never create an inferred condition group.
- Reports with no qualifying trusted condition appear under `Uncategorized`.
- One report may appear in multiple condition groups without duplicating its private file.

## Display names

Drive shows the current report display filename. A user rename takes precedence over generated naming, while the original filename remains provenance.

## Exclusions

Incomplete uploads and reports needing profile assignment do not appear in a profile's Drive.
