## 1. Alembic Foundation

- [ ] 1.1 Add Alembic to project dependencies and create its configuration.
- [ ] 1.2 Wire the migration environment to application settings and SQLAlchemy metadata.
- [ ] 1.3 Generate and review an initial revision for every current model, index, and constraint.

## 2. Runtime Integration

- [ ] 2.1 Separate local/test metadata bootstrap from production application startup.
- [ ] 2.2 Add documented upgrade, current-revision, and downgrade commands.
- [ ] 2.3 Define the safe stamp or recreation path for existing local SQLite databases.

## 3. Verification

- [ ] 3.1 Test upgrading an empty database to head and compare it with the model contract.
- [ ] 3.2 Test production startup against the expected schema without metadata creation.
- [ ] 3.3 Test downgrade behavior for the initial reversible revision.
- [ ] 3.4 Run the backend test suite and strict OpenSpec validation.
