## ADDED Requirements

### Requirement: India-resident managed production persistence
The production service SHALL persist all application-controlled relational medical data in a Supabase Postgres project provisioned in `ap-south-1` (Mumbai) through the versioned schema, and SHALL NOT route that data to another region.

#### Scenario: Production write
- **WHEN** an authenticated production request or authorized background worker creates or updates a supported resource
- **THEN** the resource SHALL be committed to the configured Mumbai Supabase Postgres project
- **AND** a subsequent service instance SHALL be able to read it subject to account ownership rules

#### Scenario: Missing or unverifiable production database boundary
- **WHEN** the production database configuration is missing, names a different project or region, or cannot be verified against the deployment attestation
- **THEN** the production data capability SHALL fail closed
- **AND** it SHALL NOT fall back to SQLite, local storage, another Supabase project, or another region

### Requirement: Database-enforced account ownership
Every private production table SHALL enforce row-level access using a verified authenticated-account or trusted-worker context, including accounts, profiles, records, web-upload ingestions, source parts, source provenance, extraction jobs and attempts, raw and normalized extraction output, observations, memory candidates, conversations and citations, deletion jobs, failure envelopes, and object metadata.

#### Scenario: Authenticated owner database access
- **WHEN** an API transaction begins with a verified Supabase subject
- **THEN** the service SHALL set transaction-local verified claims and an RLS-subject role before any application query
- **AND** row-level policies SHALL permit only resources owned by the subject's account
- **AND** transaction completion SHALL clear that identity before the connection returns to the pool

#### Scenario: Cross-account database access
- **WHEN** a database operation attempts to read or mutate a medical row owned by another account
- **THEN** row-level policies SHALL deny the operation even if an application query omitted its ownership filter

#### Scenario: Authorized background operation
- **WHEN** an extraction or cleanup worker starts work from an opaque persisted work identifier
- **THEN** a restricted database function SHALL derive the owning account from persisted state and establish transaction-local worker context
- **AND** the worker SHALL be restricted by RLS and task-specific grants to that account and operation

#### Scenario: Forged worker scope
- **WHEN** a worker caller supplies another account identifier or a work identifier outside its granted task class
- **THEN** the database SHALL refuse to establish the requested context
- **AND** no private row SHALL be disclosed or mutated

#### Scenario: Unscoped privileged access
- **WHEN** a normal API or worker path lacks valid scoped identity
- **THEN** the path SHALL fail closed
- **AND** it SHALL NOT use a database owner, Supabase service-role credential, or role with `BYPASSRLS`

### Requirement: Stable private production object storage
Production report files SHALL be stored in non-public Supabase Storage buckets under opaque account/ingestion/part object keys, and retained raw extraction outputs SHALL use opaque account/ingestion/attempt object keys; both key families SHALL be independent of patient profiles.

#### Scenario: Store a report source part
- **WHEN** an authenticated `direct_file` or `camera` web upload durably stores a source part through the backend
- **THEN** the service SHALL use a key shaped as `accounts/{account_id}/ingestions/{ingestion_id}/parts/{part_id}/{object_id}`
- **AND** the key SHALL NOT contain a profile identifier, account contact data, original filename, document issuer, or clinical/display text
- **AND** protected metadata SHALL reference the private bucket and opaque key without exposing a public URL

#### Scenario: Client attempts direct-to-storage upload
- **WHEN** a browser or other normal client attempts to create, replace, sign, or choose the object path for a report directly in Supabase Storage
- **THEN** storage policy SHALL deny the operation
- **AND** supported V1 uploads SHALL continue through authenticated backend routes that validate the content and stamp `direct_file` or `camera`

#### Scenario: Assign or reassign a report
- **WHEN** an ingestion is assigned or reassigned to an owned profile
- **THEN** the service SHALL update relational ownership links without copying, renaming, or changing any source object key

#### Scenario: Store retained raw extraction output
- **WHEN** a successful extraction attempt retains encrypted raw output
- **THEN** the service SHALL use a key shaped as `accounts/{account_id}/ingestions/{ingestion_id}/attempts/{attempt_id}/{object_id}`
- **AND** retry or supersession SHALL create a new attempt identifier without changing any source-part key

#### Scenario: Request private object access
- **WHEN** an authenticated account owner requests an accessible report object
- **THEN** application authorization and storage policy SHALL verify account ownership
- **AND** the backend MAY return a single-object signed read URL valid for no more than 60 seconds
- **AND** the URL SHALL NOT be persisted or emitted to logs, traces, analytics, queues, Feed responses, or list responses

#### Scenario: Cross-account object request
- **WHEN** a user attempts to read, sign, replace, or delete an object outside their account
- **THEN** application authorization and storage policy SHALL deny the operation

#### Scenario: Missing production storage configuration
- **WHEN** the Mumbai private bucket or required storage policy is unavailable or unverifiable
- **THEN** production storage operations SHALL fail closed
- **AND** they SHALL NOT write to a public bucket, local filesystem, or another region

### Requirement: Bounded Mumbai extraction storage
Textract staging/output and associated SNS/SQS resources SHALL be separate encrypted resources in AWS `ap-south-1`, SHALL use least-privilege workload access, and SHALL NOT become the durable report store.

#### Scenario: Process a Textract document
- **WHEN** a source document requires Textract
- **THEN** input and customer-controlled Textract output SHALL use private, customer-KMS-encrypted Mumbai staging resources
- **AND** the worker SHALL delete both staging copies immediately after durable result persistence or terminal cleanup
- **AND** lifecycle rules SHALL expire any surviving staging object within 24 hours

#### Scenario: Detect stale transient data
- **WHEN** a Textract staging or output object survives its expected cleanup window
- **THEN** reconciliation SHALL emit an operational alert and retry idempotent deletion without exposing object contents

### Requirement: Deletion and bounded residual metadata
Deleting a report SHALL revoke access immediately and SHALL idempotently purge its durable content, retained raw output, derivatives, and transient processing copies while preserving only explicitly bounded non-PHI operational records.

#### Scenario: Delete a report
- **WHEN** an authorized account owner deletes a report
- **THEN** the service SHALL tombstone the report, revoke new signed access, cancel dispatchable work, and record cleanup atomically
- **AND** Feed, detail, and download paths SHALL stop exposing the report immediately
- **AND** idempotent cleanup SHALL purge its source objects, raw and normalized extraction output, extracted fields, observations, report-derived memory, and known AWS transient objects

#### Scenario: Retry partial cleanup
- **WHEN** deletion succeeds at the authorization boundary but one storage or provider cleanup action fails
- **THEN** the content SHALL remain inaccessible
- **AND** cleanup SHALL retry from durable state without restoring the report or duplicating side effects

#### Scenario: Retain a safe failure envelope
- **WHEN** a web upload or extraction attempt fails without producing a report
- **THEN** retained failure metadata SHALL contain only enumerated status/failure codes, route channel metadata, timestamps, and opaque internal identifiers
- **AND** it SHALL expire exactly 30 days after terminal failure

### Requirement: Restricted retained extraction output
Successful native, Textract, and Bedrock raw output SHALL be encrypted within the application-controlled private boundary, inaccessible to routine user and support queries, and retained only until its source report is deleted.

#### Scenario: Persist successful raw output
- **WHEN** an extraction attempt succeeds
- **THEN** its raw provider output SHALL be encrypted and account-scoped
- **AND** only a dedicated audited operational role MAY read it
- **AND** user-facing responses, logs, analytics, traces, and queue messages SHALL NOT contain it

#### Scenario: Delete the source report
- **WHEN** cleanup purges the source report
- **THEN** all successful raw output for that report and its superseded attempts SHALL also be purged

### Requirement: Migration and capability gates
Production capabilities SHALL remain disabled until their migrations, region controls, ownership policies, secrets, lifecycle controls, and isolation tests have passed in a disposable environment and the target deployment.

#### Scenario: Enable the base production boundary
- **WHEN** an operator enables production Postgres and private Storage
- **THEN** the schema revision, Mumbai project attestation, RLS policies, storage policies, encryption keys, deletion reconciliation, backup/restore check, and two-account isolation suite SHALL all be current and passing
- **AND** a failed check SHALL keep the capability disabled

#### Scenario: Enable production extraction
- **WHEN** an operator enables production Textract and Bedrock processing
- **THEN** the base boundary, Mumbai staging/queue controls, provider privacy approval, and Bedrock zero-data-retention eligibility SHALL pass
- **AND** failure SHALL NOT fall back to mock extraction, privileged data access, cross-region inference, or another provider

#### Scenario: Exercise fresh-schema migration
- **WHEN** an empty database is upgraded to the declared head and representative private data is created through current application flows
- **THEN** checksums and row counts SHALL verify that source objects and protected rows are neither lost nor exposed
- **AND** feature-disable rollback SHALL preserve the Mumbai Supabase boundary, RLS, tombstones, and in-progress deletion cleanup

### Requirement: Local adapter parity
Local development and tests SHALL retain adapters that implement the same application-facing persistence, private-storage, authorization, stable-key, signed-access, and lifecycle contracts without claiming production residency or provider guarantees.

#### Scenario: Run locally
- **WHEN** the service runs in an explicitly local environment
- **THEN** it MAY use SQLite and local private storage without requiring Supabase or AWS data services
- **AND** API response and ownership behavior SHALL remain compatible with production

#### Scenario: Run shared contracts
- **WHEN** the persistence, storage, or deletion contract suite runs against local and production adapters
- **THEN** both SHALL enforce stable ingestion keys, account isolation, access revocation, and idempotent cleanup semantics
