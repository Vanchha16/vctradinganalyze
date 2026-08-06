"""Safe local launchers for the API server, Celery worker, and Celery
beat scheduler (cleanup spec: dev-runtime vendor isolation).

`backend/tests/conftest.py` only ever protected the *pytest session* from
ambient `backend/.env` - a manually-started `uvicorn`/`celery worker`/
`celery beat` still read the real file, including real vendor API keys.
That gap is how a real Twelve Data quota got exhausted and a real
NewsAPI call went out during local development (BACKLOG.md §11/§16).
This script makes the safe path the *default* path for all three
processes, using the same canonical override set `conftest.py` now
shares via `local_env.py`.

**Design: subprocess handoff, not in-process overrides.** Unlike
`conftest.py` (which must set `os.environ` before its *own* first
`app.*` import, since pytest imports it in-process), this script never
imports any `app.*` module itself at all. It builds an environment dict,
prints a banner from that dict alone, and hands off to the real
`uvicorn`/`celery` command via `subprocess.run(..., env=...)`. The child
process inherits the already-correct environment and does its own
`app.*` imports fresh - there is no import-ordering hazard to get wrong
here, which is deliberately more robust for a long-running server than
trying to preserve import order across `uvicorn`'s/Celery's own internal
startup machinery.

**This script never reads `backend/.env`.** In `--real-providers` mode
it simply does not apply the mock overrides, so the child process reads
`.env` itself, the normal way - this launcher never opens, parses, or
prints that file's contents (rule 9, never expose secrets).

Usage:
    python scripts/run_dev.py api                  # mock providers (default)
    python scripts/run_dev.py worker
    python scripts/run_dev.py beat
    python scripts/run_dev.py api --real-providers  # deliberate opt-in only
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from local_env import SAFE_LOCAL_OVERRIDES, apply_safe_overrides  # noqa: E402

_BACKEND_DIR = Path(__file__).resolve().parent.parent

_COMMANDS: dict[str, list[str]] = {
    "api": [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--reload",
    ],
    "worker": [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "app.workers.celery_app.celery_app",
        "worker",
        "--loglevel=info",
    ],
    "beat": [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "app.workers.celery_app.celery_app",
        "beat",
        "--loglevel=info",
    ],
}


def _print_banner(mode: str, real_providers: bool) -> None:
    print("=" * 64)
    print(f"ClaudeTrading AI - local '{mode}' (scripts/run_dev.py)")
    print("=" * 64)
    if real_providers:
        print("Mode: REAL PROVIDERS (--real-providers was passed)")
        print("backend/.env is used as-is and is NOT read or displayed by this")
        print("launcher - whatever real vendors/keys it configures are now live.")
        print("This can call a real vendor API and consume real quota.")
    else:
        print("Mode: MOCK PROVIDERS (default - safe, no vendor is ever called)")
        for key, value in SAFE_LOCAL_OVERRIDES.items():
            print(f"  {key}={value}")
    print("=" * 64)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safe local launcher for the API server, Celery worker, or Celery beat."
    )
    parser.add_argument("mode", choices=sorted(_COMMANDS))
    parser.add_argument(
        "--real-providers",
        action="store_true",
        help=(
            "Opt into whatever backend/.env actually configures instead of the "
            "default mock providers. May call a real vendor API. Never the default."
        ),
    )
    args = parser.parse_args()

    env = os.environ.copy()
    if not args.real_providers:
        apply_safe_overrides(env)

    _print_banner(args.mode, args.real_providers)

    result = subprocess.run(_COMMANDS[args.mode], cwd=_BACKEND_DIR, env=env, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
