"""Run the web client and local API together until interrupted."""

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "apps" / "web"


def stop(_signum, _frame):
    raise KeyboardInterrupt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--port",
        type=int,
        default=os.environ.get("CONDUCTOR_PORT", "55020"),
        help="frontend port (default: CONDUCTOR_PORT or 55020); backend uses the next port",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="reinstall the frontend's locked dependencies",
    )
    parser.add_argument(
        "--hosted-data",
        action="store_true",
        help="use the attested Supabase DB and Storage; never run hosted migrations",
    )
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65534:
        parser.error("--port must be between 1024 and 65534")

    settings = {**dotenv_values(args.env_file), **os.environ}
    missing = [
        key for key in ("SUPABASE_URL", "SUPABASE_ANON_KEY") if not settings.get(key)
    ]
    if missing:
        parser.error(
            f"Set {', '.join(missing)} in the root .env before starting the app."
        )
    node, npm = shutil.which("node"), shutil.which("npm")
    if not node or not npm:
        parser.error("Install Node.js and npm before starting the frontend.")
    for port in (args.port, args.port + 1):
        try:
            with socket.socket() as listener:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind(("127.0.0.1", port))
        except OSError:
            parser.error(
                f"Port {port} is in use. Stop the existing server or use --port <number>."
            )

    context = ROOT / ".context"
    context.mkdir(exist_ok=True)
    backend_env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{context / 'verification.db'}",
        "DATA_BACKEND": "local",
        "ENVIRONMENT": "local",
        "LOCAL_STORAGE_ROOT": str(context / "verification-storage"),
        "DEV_AUTH_ENABLED": "false",
        "SUPABASE_URL": settings["SUPABASE_URL"],
        "PYTHONUNBUFFERED": "1",
    }
    if args.hosted_data:
        from app.config import Settings
        from app.data_boundary import validate_data_settings, verify_database_boundary
        from app.database import configure_database, get_engine, require_current_database_schema

        hosted = Settings(
            _env_file=args.env_file,
            data_backend="supabase",
            environment="production",
            dev_auth_enabled=False,
            extraction_provider="disabled",
            extraction_run_inline=False,
        )
        try:
            validate_data_settings(hosted)
            configure_database(hosted.database_url)
            require_current_database_schema()
            verify_database_boundary(get_engine(), hosted)
        except Exception:
            parser.error("Hosted data preflight failed. Follow infra/supabase/README.md; no servers were started.")
        backend_env.update({key: value for key, value in settings.items() if value is not None})
        backend_env.update({
            "DATA_BACKEND": "supabase", "ENVIRONMENT": "production", "DEV_AUTH_ENABLED": "false",
            "EXTRACTION_PROVIDER": "disabled", "EXTRACTION_RUN_INLINE": "false",
        })
    frontend_env = {
        **os.environ,
        "VITE_SUPABASE_URL": settings["SUPABASE_URL"],
        "VITE_SUPABASE_ANON_KEY": settings["SUPABASE_ANON_KEY"],
        "VITE_API_BASE_URL": "/api",
        "API_PROXY_TARGET": f"http://127.0.0.1:{args.port + 1}",
    }

    children: list[subprocess.Popen] = []
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        if args.install or not (WEB / "node_modules" / ".package-lock.json").exists():
            subprocess.run([npm, "ci"], cwd=WEB, check=True)
        # Only the workspace-local SQLite database is migrated by this command.
        if not args.hosted_data:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alembic",
                    "-c",
                    "apps/api/alembic.ini",
                    "upgrade",
                    "head",
                ],
                cwd=ROOT,
                env=backend_env,
                check=True,
            )
        print(f"Frontend: http://localhost:{args.port}", flush=True)
        print(f"Backend:  http://localhost:{args.port + 1}/docs", flush=True)
        print(
            ("Using private Supabase DB and Storage." if args.hosted_data
             else "Using .context/verification.db.") + " Press Ctrl+C to stop both servers.",
            flush=True,
        )
        # Keep both servers in our process group so Conductor can stop the entire run.
        # Start Vite directly to avoid leaving an npm wrapper's child behind on shutdown.
        children.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.port + 1),
                    "--reload",
                ],
                cwd=ROOT,
                env=backend_env,
            )
        )
        children.append(
            subprocess.Popen(
                [
                    node,
                    str(WEB / "node_modules" / "vite" / "bin" / "vite.js"),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.port),
                    "--strictPort",
                ],
                cwd=WEB,
                env=frontend_env,
            )
        )
        while all(child.poll() is None for child in children):
            time.sleep(0.25)
        failed = next(child for child in children if child.poll() is not None)
        print("A server exited; stopping both. See the logs above.", file=sys.stderr)
        return failed.returncode or 1
    except KeyboardInterrupt:
        print("\nStopping both servers…", flush=True)
        return 0
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Could not start the app: {exc}", file=sys.stderr)
        return 1
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
