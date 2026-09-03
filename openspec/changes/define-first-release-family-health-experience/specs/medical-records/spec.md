## MODIFIED Requirements

### Requirement: Manage records within an owned profile
An authenticated account manager SHALL be able to stage an account-owned ingestion before patient assignment and SHALL be able to list and retrieve completed medical records after they resolve to an owned profile.

#### Scenario: Stage a new ingestion
- **WHEN** the account manager starts a supported file-selection or camera upload through the authenticated web interface
- **THEN** the service SHALL create an account-owned staged ingestion without requiring a final family profile

#### Scenario: Finalize a resolved record
- **WHEN** upload is complete and patient assignment resolves to an owned profile
- **THEN** the service SHALL create or finalize the medical record under that account and profile
- **AND** the record SHALL retain independent upload, assignment, extraction, and review states

#### Scenario: List profile records
- **WHEN** a user lists records for an owned profile
- **THEN** the service SHALL return only that account's completed records resolved to the profile
- **AND** the service SHALL order the records by newest creation time first

#### Scenario: Use an unavailable profile
- **WHEN** a user attempts to resolve, create, or list records using a missing or unowned profile
- **THEN** the service SHALL return HTTP 404

### Requirement: Private file upload
The service SHALL accept unencrypted PDF, JPEG, and PNG source parts submitted through the authenticated web interface for an account-owned ingestion and store them below a stable private account-and-ingestion boundary without returning an internal storage path or requiring a final profile in the object identity.

#### Scenario: Successful upload
- **WHEN** all source parts within the configured limits are accepted for an owned ingestion
- **THEN** the service SHALL persist the private content under a stable account and ingestion or record identity
- **AND** the response SHALL expose safe file metadata but not an internal storage path

#### Scenario: Oversized upload
- **WHEN** a logical document exceeds 15,000,000 bytes or 20 pages/parts, or an image exceeds 10,000,000 bytes or 10,000 pixels in either dimension
- **THEN** the service SHALL delete or invalidate partial content from that attempt
- **AND** the service SHALL return HTTP 413
- **AND** the ingestion SHALL NOT become upload complete

### Requirement: Explicit AI-processing consent
The service SHALL create an extraction job for every upload-complete logical document under the owning account's accepted AI-processing consent, and SHALL snapshot the accepted consent version on the ingestion without asking again for each document. Accepted consent SHALL be a precondition for uploading, and the service SHALL fail closed rather than retain a document that has no governing consent.

#### Scenario: Upload under accepted account consent
- **WHEN** a file upload completes for an account with accepted AI-processing consent
- **THEN** the service SHALL record the governing consent version on the ingestion
- **AND** the service SHALL create an extraction job for that file or logical multi-image document

#### Scenario: Upload from an account without accepted consent
- **WHEN** an upload is attempted for an account that has not accepted AI-processing consent
- **THEN** the service SHALL reject the upload with HTTP 403
- **AND** the service SHALL NOT retain any part of that upload

#### Scenario: Upload another document under existing consent
- **WHEN** an account with accepted consent uploads another document
- **THEN** the service SHALL NOT require another per-document consent choice

## ADDED Requirements

### Requirement: Stage and complete a logical document upload
The service SHALL represent file receipt separately from profile assignment, extraction, and review, and SHALL mark an upload complete only after every source part, immutable source-provenance field, and required file metadata are stored successfully.

#### Scenario: Upload one image or PDF
- **WHEN** a user submits one supported image or PDF and storage completes
- **THEN** the service SHALL create one complete logical document
- **AND** the service SHALL retain its account ownership, original filename, source channel, and upload completion time

#### Scenario: Upload multiple images as one document
- **WHEN** a user submits an ordered set of supported images as one report
- **THEN** the service SHALL preserve the image order
- **AND** the service SHALL finalize one logical document only after every image is stored

#### Scenario: Capture a document with the camera
- **WHEN** the client submits supported image data captured by a camera
- **THEN** the service SHALL process it through the same private upload contract as another supported image
- **AND** the authenticated camera route SHALL stamp `source_channel=camera`

#### Scenario: Select a file directly
- **WHEN** the client submits a file through the authenticated file-selection route
- **THEN** that route SHALL stamp `source_channel=direct_file`

#### Scenario: Override the route-controlled source channel
- **WHEN** a client attempts to supply or change the `source_channel` instead of using the value stamped by the authenticated file-selection or camera route
- **THEN** the service SHALL reject the request

#### Scenario: A multipart upload is incomplete
- **WHEN** one or more required parts fail validation or storage
- **THEN** the service SHALL NOT mark the logical document upload complete
- **AND** the incomplete upload SHALL NOT appear in Feed or Drive

#### Scenario: Upload unsupported content
- **WHEN** submitted content is empty, corrupt, encrypted without usable access, oversized, or outside the supported PDF and image formats
- **THEN** the service SHALL reject or fail the upload with an actionable safe reason
- **AND** no partial content SHALL become a completed record

### Requirement: Capture user-supplied report context
The service SHALL allow optional descriptive context and a display filename for a staged or completed owned document while keeping them distinguishable from extracted clinical evidence.

#### Scenario: Add optional context
- **WHEN** the account manager supplies valid additional information with an upload
- **THEN** the service SHALL store it as user-authored context
- **AND** it SHALL NOT become a medical-memory fact solely because it was supplied to extraction

#### Scenario: Preserve file identity
- **WHEN** a document is accepted
- **THEN** the service SHALL preserve its original filename for audit
- **AND** the service MAY use a separate display filename in user-facing views

### Requirement: Retain canonical ingestion source provenance
Every V1 ingestion source SHALL use `direct_file` or `camera` as stamped by its authenticated web-upload route and SHALL retain immutable account, receipt time, actor ID, source-part ordinal, original filename, detected MIME type, byte count, SHA-256, grouping identity, and authorization basis.

#### Scenario: Complete an ingestion
- **WHEN** every ordered source part and required provenance field is stored
- **THEN** the completed source tag and part provenance SHALL become immutable

#### Scenario: Read owned provenance
- **WHEN** the account manager opens owned report detail
- **THEN** the service SHALL expose the channel and safe source label
- **AND** it SHALL NOT expose credentials, authorization details, or internal storage keys

### Requirement: Resolve the document's family profile safely
The service SHALL treat the profile selected in Upload as provisional and SHALL automatically select an existing owned profile only when source-linked patient evidence exactly matches one normalized full name or explicit alias. Patient evidence MAY carry a source-linked date of birth from the document, but assignment SHALL ignore it because profiles do not store date of birth. The provisional selection alone SHALL NOT resolve a document.

#### Scenario: Extracted patient matches the selected profile
- **WHEN** Unicode NFKC, case-folded, trimmed, whitespace-collapsed patient evidence exactly matches only the provisionally selected profile
- **THEN** the service SHALL resolve the document to that profile

#### Scenario: Extracted patient matches another owned profile
- **WHEN** normalized patient evidence exactly matches only a different existing owned profile or explicit alias
- **THEN** the service SHALL resolve the document to the extracted match
- **AND** the service SHALL retain the provisional selection and match evidence for audit

#### Scenario: Extracted patient is ambiguous or unmatched
- **WHEN** no profile matches exactly, multiple profiles match exactly, or only fuzzy, partial, phonetic, or scored similarity exists
- **THEN** the service SHALL mark the document as needing profile assignment
- **AND** the service SHALL NOT publish metric observations or medical-memory facts for that document
- **AND** the service SHALL NOT create a family profile from extracted output

#### Scenario: User resolves pending assignment
- **WHEN** the account manager assigns a pending document to an owned profile
- **THEN** the service SHALL resolve the document and make its eligible derived data available under only that profile

### Requirement: Manage an owned report file
The account manager SHALL be able to download, rename, and delete a completed report they own without exposing internal private-storage paths.

#### Scenario: Download an owned report
- **WHEN** the account manager requests a download for an owned completed report
- **THEN** the service SHALL authorize the request at access time
- **AND** the service SHALL deliver the private content without exposing a public or internal storage path

#### Scenario: Rename an owned report
- **WHEN** the account manager supplies a valid new display filename
- **THEN** the service SHALL update the display filename
- **AND** the service SHALL preserve the original filename and stored-object identity

#### Scenario: Delete an owned report
- **WHEN** the account manager confirms deletion of an owned report
- **THEN** the service SHALL make the source file and report inaccessible immediately
- **AND** the service SHALL prevent further extraction work
- **AND** the service SHALL remove or invalidate sensitive source provenance, raw extraction output, derived fields, metric observations, medical-memory facts, and private stored content associated only with that report

#### Scenario: Manage another account's report
- **WHEN** a user requests download, rename, or deletion for a report owned by another account
- **THEN** the service SHALL respond as though the report was not found
