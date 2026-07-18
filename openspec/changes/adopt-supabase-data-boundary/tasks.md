## 1. Production Database Boundary

- [ ] 1.1 Complete `add-database-migrations` and provision a disposable Supabase test environment.
- [ ] 1.2 Spike and select a request-scoped database identity approach that does not bypass RLS.
- [ ] 1.3 Configure production SQLAlchemy persistence with fail-closed environment validation.
- [ ] 1.4 Add row-level policies for every user-owned table through migrations.
- [ ] 1.5 Add two-user integration tests for read, insert, update, and delete isolation.

## 2. Private Object Storage

- [ ] 2.1 Extract an application-facing private storage interface from the local adapter.
- [ ] 2.2 Provision a non-public bucket and owner-scoped object policies.
- [ ] 2.3 Implement the Supabase storage adapter with upload limits and cleanup on metadata failure.
- [ ] 2.4 Add shared adapter contract tests and cross-user object-access tests.

## 3. Rollout

- [ ] 3.1 Document required secrets, provisioning, migration, backup, and rollback procedures.
- [ ] 3.2 Add a checked migration path for existing records and files, if any exist.
- [ ] 3.3 Verify production mode cannot fall back to SQLite or local filesystem storage.
- [ ] 3.4 Run the backend test suite, Supabase integration tests, and strict OpenSpec validation.
- [ ] 3.5 Complete implementation review and finalize `review.md` with the reviewed commit, test evidence, findings, and resume state.
