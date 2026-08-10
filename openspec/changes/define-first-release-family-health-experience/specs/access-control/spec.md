## MODIFIED Requirements

### Requirement: User-owned resource isolation
The service SHALL scope every private account resource to the authenticated account, including profiles, records, staged uploads, source provenance, source parts, files, extraction attempts and results, metric observations, medical memory, conversations, appointments, checklists, and reviews.

#### Scenario: Owner accesses a resource
- **WHEN** an authenticated account manager requests a resource owned by their account
- **THEN** the service SHALL allow the operation subject to the resource's other validation rules

#### Scenario: User requests another owner's resource
- **WHEN** an authenticated user requests any private resource owned by another account
- **THEN** the service SHALL respond as though that resource was not found

#### Scenario: Derived view is requested
- **WHEN** an authenticated user requests a feed, organization view, metric series, or conversation
- **THEN** every returned source and derived item SHALL belong to that user's account

### Requirement: Protect authenticated web-upload ingress
Only authenticated web-upload routes SHALL create `direct_file` or `camera` source provenance, and every created upload resource SHALL carry the authenticated owning account.

#### Scenario: Authenticated account creates an upload
- **WHEN** an account manager submits a file or camera capture through a supported web-upload route
- **THEN** the service SHALL stamp the route-controlled source channel and authenticated owning account

#### Scenario: Caller claims protected upload provenance
- **WHEN** a caller attempts to supply a different owning account or override route-controlled source provenance
- **THEN** the service SHALL reject the request without revealing whether another account exists
