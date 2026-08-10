# Applications

- `api/` contains the implemented FastAPI backend and background-worker entrypoint.
- `web/` is reserved for the V1 web client. No web framework has been selected or scaffolded.
- `ios/` is the planned V2 native iOS location and will be created when that work begins.
- `android/` is the planned V2 native Android location and will be created when that work begins.

All clients will use the backend's authenticated HTTP API. They will not connect directly to
Postgres, queues, OCR/model providers, or private object-storage keys.
