## MODIFIED Requirements

### Requirement: User-owned resource isolation
The service SHALL scope every private account resource to the authenticated account, including profiles, records, staged ingestions, files, extraction jobs, extracted fields, metric observations, medical memory, conversations, connector state, appointments, checklists, and reviews.

#### Scenario: Owner accesses a resource
- **WHEN** an authenticated account manager requests a resource owned by their account
- **THEN** the service SHALL allow the operation subject to the resource's other validation rules

#### Scenario: User requests another owner's resource
- **WHEN** an authenticated user requests any private resource owned by another account
- **THEN** the service SHALL respond as though that resource was not found

#### Scenario: Derived view is requested
- **WHEN** an authenticated user requests a feed, organization view, metric series, or conversation
- **THEN** every returned source and derived item SHALL belong to that user's account

