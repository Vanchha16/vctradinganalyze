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
    python scripts/run_dev.py api                     # mock providers (default), port 8000
    python scripts/run_dev.py api --port 8001          # match a non-default local setup
    python scripts/run_dev.py worker
    python scripts/run_dev.py beat
    python scripts/run_dev.py api --real-providers     # deliberate opt-in only
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from local_env import SAFE_LOCAL_OVERRIDES, apply_safe_overrides  # noqa: E402

_BACKEND_DIR = Path(__file__).resolve().parent.parent

#: 8000 is this project's canonical backend port (`frontend/services/
#: api-client.ts`, `.env.example`, `docker-compose.yml`'s `uvicorn`
#: command and `${BACKEND_PORT:-8000}` mapping all agree) - `--port`
#: exists to match a machine-specific override, not to change the
#: default.
_DEFAULT_PORT = 8000

#: Must match `Settings.trusted_proxy_ips`'s default (`app/config/
#: settings.py`) - duplicated rather than imported, since this script
#: deliberately never imports any `app.*` module (see module docstring).
#: An OS-level `TRUSTED_PROXY_IPS` env var (not `.env` - this script never
#: reads that file) overrides it, same as any other setting here.
#: `--proxy-headers` is passed explicitly rather than relied on as
#: uvicorn's own default, so behavior doesn't silently change if that
#: default ever does (Phase 9A, ADR-132, docs/60 §4.1).
_DEFAULT_TRUSTED_PROXY_IPS = "127.0.0.1"

#: `worker`/`beat` take no port - only built here, not parameterized,
#: since `--port` is meaningless for either.
_STATIC_COMMANDS: dict[str, list[str]] = {
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

_MODE_CHOICES = sorted({"api", *_STATIC_COMMANDS})


def _build_api_command(port: int, trusted_proxy_ips: str) -> list[str]:
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
        "--proxy-headers",
        "--forwarded-allow-ips",
        trusted_proxy_ips,
        "--reload",
    ]


def _print_banner(mode: str, real_providers: bool, port: int, trusted_proxy_ips: str) -> None:
    # `flush=True` on every line: Python fully buffers stdout when it is
    # not a TTY (piped/redirected to a file), so a long-running server's
    # banner could otherwise sit unflushed indefinitely - exactly when an
    # unattended operator most needs to see which mode is live (found
    # during the 9ccd471 verification, only visible there because `-u`
    # happened to be passed).
    print("=" * 64, flush=True)
    print(f"ClaudeTrading AI - local '{mode}' (scripts/run_dev.py)", flush=True)
    if mode == "api":
        print(f"Port: {port}", flush=True)
        print(f"Trusted proxy IPs (--forwarded-allow-ips): {trusted_proxy_ips}", flush=True)
    print("=" * 64, flush=True)
    if real_providers:
        print("Mode: REAL PROVIDERS (--real-providers was passed)", flush=True)
        print("backend/.env is used as-is and is NOT read or displayed by this", flush=True)
        print("launcher - whatever real vendors/keys it configures are now live.", flush=True)
        print("This can call a real vendor API and consume real quota.", flush=True)
    else:
        print("Mode: MOCK PROVIDERS (default - safe, no vendor is ever called)", flush=True)
        for key, value in SAFE_LOCAL_OVERRIDES.items():
            print(f"  {key}={value}", flush=True)
    print("=" * 64, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safe local launcher for the API server, Celery worker, or Celery beat."
    )
    parser.add_argument("mode", choices=_MODE_CHOICES)
    parser.add_argument(
        "--port",
        type=int,
        default=_DEFAULT_PORT,
        help=(
            f"Port for the 'api' mode's uvicorn server (default {_DEFAULT_PORT}, "
            "this project's canonical port). Meaningless for worker/beat."
        ),
    )
    parser.add_argument(
        "--real-providers",
        action="store_true",
        help=(
            "Opt into whatever backend/.env actually configures instead of the "
            "default mock providers. May call a real vendor API. Never the default."
        ),
    )
    args = parser.parse_args()

    if args.mode != "api" and args.port != _DEFAULT_PORT:
        parser.error(f"--port is only meaningful for the 'api' mode (got mode={args.mode!r}).")

    env = os.environ.copy()
    if not args.real_providers:
        apply_safe_overrides(env)

    trusted_proxy_ips = env.get("TRUSTED_PROXY_IPS", _DEFAULT_TRUSTED_PROXY_IPS)

    _print_banner(args.mode, args.real_providers, args.port, trusted_proxy_ips)

    if args.mode == "api":
        command = _build_api_command(args.port, trusted_proxy_ips)
    else:
        command = _STATIC_COMMANDS[args.mode]
    result = subprocess.run(command, cwd=_BACKEND_DIR, env=env, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
