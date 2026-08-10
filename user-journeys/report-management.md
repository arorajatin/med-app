# Report Management Journey

## Goal

Give the account manager control over each owned report and its private source file.

## Download

1. The account manager opens an owned completed report.
2. The account manager chooses Download.
3. The service authorizes ownership at request time.
4. The private content is delivered without exposing a public URL or internal object key.

## Rename

1. The account manager chooses Rename.
2. The account manager enters a valid non-empty display filename.
3. Feed, Drive, and report details show the new display filename.
4. The original source filename and stored-object identity remain unchanged for provenance.

## Delete

1. The account manager chooses Delete.
2. The app explains that the source and report-derived health data will no longer be available.
3. The account manager confirms.
4. The report disappears immediately from Feed, Drive, download, metrics, memory, and future Chat retrieval.
5. Pending extraction work stops.
6. Private content and report-only extraction output, observations, and memory are purged through retryable cleanup.
7. Existing Chat citations retain only a non-private `Source unavailable` marker.

## Failure and access behavior

- Download, rename, and delete for a missing or foreign report behave as unavailable.
- A transient purge failure never restores user access to a tombstoned report.
- Archive and general post-review reassignment are outside the first release.

