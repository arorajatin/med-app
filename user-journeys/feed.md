# Feed Journey

## Goal

Provide one chronological stream of successfully uploaded family reports.

## Journey

1. The account manager opens Feed.
2. Feed lists upload-complete reports from every family profile and ingestion source.
3. Each item shows:
   - assigned family member or `Needs assignment`;
   - current display filename;
   - direct, camera, email, or WhatsApp source;
   - upload and trusted report dates when available;
   - assignment, extraction, and review state.
4. The account manager chooses upload-date or report-date ordering.
5. Ordering is newest first.
6. Opening an item leads to assignment, processing status, review, observations, or report details as appropriate.

## Inclusion rule

Feed includes a report once private upload is complete. Extraction may still be queued, running, failed, or awaiting review. A completed unresolved report appears with an attention state.

Receiving, partial, and failed uploads do not appear as completed Feed items.

## Ordering

- **Upload date** uses upload completion time descending.
- **Report date** uses confirmed, edited, or user-entered report date descending.
- In report-date mode, undated reports appear after dated reports and use upload completion time among themselves.
- Stable identifiers resolve remaining ties.

## Access behavior

Feed is always account-wide, but every source item remains private to the authenticated account.

