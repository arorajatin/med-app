import sys

from app.ai.mock_provider import MockExtractor
from app.config import get_settings
from app.database import configure_database, get_db, init_db
from app.models import ExtractionJob
from app.services.extraction import run_extraction_job
from app.storage import LocalPrivateStorage


def run_once() -> int:
    settings = get_settings()
    configure_database(settings.database_url)
    init_db()

    db = next(get_db())
    try:
        job = db.query(ExtractionJob).filter(ExtractionJob.status == "queued").first()
        if job is None:
            return 0
        storage = LocalPrivateStorage(settings)
        extractor = MockExtractor()
        run_extraction_job(db, job_id=job.id, storage=storage, extractor=extractor)
        return 1
    finally:
        db.close()


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else "once"
    if command != "once":
        raise SystemExit("Usage: python -m app.worker once")
    processed = run_once()
    print(f"processed_jobs={processed}")


if __name__ == "__main__":
    main()

