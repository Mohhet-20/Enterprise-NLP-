"""Start the hosted public demo (deploy/demo/Dockerfile): fresh showcase, locked accounts, then the API.

The image build already ran scripts/demo_build.py, so evaluations, the model registry and a dataset exist in
/app/showcase and a cold start on a small free instance takes seconds. On every start this:

1. copies the showcase to a fresh working directory, so each restart is a clean demo;
2. gives every existing account (the build's administrator included) a random password nobody knows;
3. when NLP_ADMIN_USERNAME and NLP_ADMIN_PASSWORD are set as hosting secrets, creates the owner's administrator
   (the normal sign-in form); visitors use "Explore the live demo" (POST /auth/guest), a non-admin guest;
4. replaces itself with uvicorn on $PORT.
"""

import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOWCASE = Path(os.environ.get("NLP_SHOWCASE_DIR", "/app/showcase"))
WORKING = Path(os.environ.get("NLP_DEMO_ROOT", "/tmp/nlp-demo"))


def main() -> int:
    if not (SHOWCASE / "nlp_platform.db").is_file():
        print(f"[demo] {SHOWCASE} has no nlp_platform.db; the image build did not produce the showcase", file=sys.stderr)
        return 2
    shutil.rmtree(WORKING, ignore_errors=True)  # previous run's database (and SQLite journals) and evaluation reports
    shutil.copytree(SHOWCASE, WORKING)
    os.environ.update({
        "ENVIRONMENT": "production",
        "DATABASE_URL": f"sqlite:///{(WORKING / 'nlp_platform.db').as_posix()}",
        "EVALUATION_RUNS_DIR": str(WORKING / "evaluation_runs"),
        "EXPERIMENTS_DIR": str(WORKING / "experiments"),
        "GUEST_ACCESS_ENABLED": "true",
        "REGISTRATION_ENABLED": "false",
    })
    if not os.environ.get("SECRET_KEY"):
        print("[demo] SECRET_KEY is not set; refusing to start a public API without a signing key", file=sys.stderr)
        return 2
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)

    from backend.auth.password import hash_password
    from backend.core.constants import UserRole
    from backend.database.session import SessionLocal
    from backend.models.user import User
    from backend.repositories.user_repository import UserRepository

    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            user.hashed_password = hash_password(secrets.token_urlsafe(32))
        owner = os.environ.get("NLP_ADMIN_USERNAME", "").strip()
        owner_password = os.environ.get("NLP_ADMIN_PASSWORD", "")
        if owner and owner_password:
            if len(owner_password) < 12:
                print("[demo] NLP_ADMIN_PASSWORD must be at least 12 characters", file=sys.stderr)
                return 2
            UserRepository(db).create(User(username=owner, email=f"{owner}@owner.nlp-demo.app",
                                           hashed_password=hash_password(owner_password), role=UserRole.ADMIN.value))
            print(f"[demo] owner administrator {owner} ready", flush=True)
        else:
            print("[demo] NLP_ADMIN_USERNAME/NLP_ADMIN_PASSWORD not set: no administrator account", flush=True)
        db.commit()
        print(f"[demo] locked {len(users)} showcase account(s); guest access on, registration off", flush=True)
    finally:
        db.close()

    cmd = [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", os.environ.get("PORT", "8000"),
           "--workers", "1", "--proxy-headers", "--no-access-log"]
    # Behind the host's proxy: client addresses (rate limits, audit) come from X-Forwarded-For.
    os.environ.setdefault("FORWARDED_ALLOW_IPS", "*")
    if os.name == "nt":  # local trial on Windows, where exec* mangles paths with spaces
        return subprocess.call(cmd)
    os.execvpe(cmd[0], cmd, os.environ)  # hand PID 1 to uvicorn so it receives SIGTERM
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
