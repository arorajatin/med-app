# Feed Journey

## Goal

Provide one chronological stream of family reports successfully uploaded through the web app.

## Journey

1. The account manager opens Feed.
2. Feed defaults to All Family, listing upload-complete reports submitted through the authenticated web-upload flow for every family profile. The account manager can select an individual family member to see reports assigned to that person.
3. Each item shows:
   - assigned family member, pending patient match, or `Needs assignment`;
   - current display filename;
   - immutable `direct_file` or `camera` source;
   - upload and trusted report dates when available;
   - assignment, extraction, and review state.
4. The account manager chooses upload-date or report-date ordering.
5. Ordering is newest first.
6. Opening an item leads to assignment, processing status, review, observations, or report details as appropriate.

After a successful upload receipt, the app opens Feed in All Family with upload-date order and highlights the new report. If the account manager has already moved to another tab, the app stays there and Upload shows the receipt on the next visit. Feed and report details refresh current states every five seconds while visible. Failed reads show an error and a refresh action; they do not imply an empty family history. Leaving Feed stops polling, and sign-out clears its private state.

The current Feed milestone includes pending assignment, processing details, and source-linked unreviewed measurements. Review editing remains a later milestone; pending metadata and medical-memory review are shown separately.

## Inclusion rule

All Family includes a report once private upload is complete. Extraction may still be queued, running, failed, or awaiting review. A completed report needing assignment appears with an attention state. Individual member views include only reports whose assignment is resolved to that person; the provisional upload selection does not determine inclusion. An empty member view links back to All Family for uploads awaiting assignment.

Receiving, partial, and failed uploads do not appear as completed Feed items.

## Ordering

- **Upload date** uses upload completion time descending.
- **Report date** uses confirmed, edited, or user-entered report date descending.
- In report-date mode, undated reports appear after dated reports and use upload completion time among themselves.
- Stable identifiers resolve remaining ties.

## Access behavior

Feed and Drive share the All Family and individual family-member view choices. Every source item remains private to the authenticated account. Switching the family view resets pagination and preserves date ordering. Returning from report details preserves the selected family view, ordering, and loaded page count.

## First-release boundary

Email, messaging, and other external ingestion sources are outside the first release and do not appear in Feed.
