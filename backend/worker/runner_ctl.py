"""Cross-process lifecycle controller for ThinkFirst Local Judge0 Code Runner.

Invoked by START_THINKFIRST_CODE_RUNNER.ps1 and STOP_THINKFIRST_CODE_RUNNER.ps1.
Never prints or logs any secret tokens.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_DIR.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from worker.execution_worker import OutboundExecutionWorker, _default_env_path  # noqa: E402


def _read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        raise RuntimeError(f"Missing runner credentials file at {path}.")
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        res = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in (res.stdout or "")
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _stop_pid_force(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True,
            text=True,
            check=False,
        )
    else:
        with contextlib.suppress(OSError):
            os.kill(pid, 9)


def _windows_detached_creation_flags() -> int:
    """Return detached Windows subprocess creation flags safely across platforms."""
    if os.name != "nt":
        return 0
    new_group = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    detached = getattr(subprocess, "DETACHED_PROCESS", 0)
    flags = 0
    if isinstance(new_group, int):
        flags |= new_group
    if isinstance(detached, int):
        flags |= detached
    return flags


def _print_banner(ok: bool, lines: list[str]) -> None:
    bar = "=" * 60
    print("")
    print(bar)
    print(f"  THINKFIRST CODE RUNNER STATUS: {'READY' if ok else 'ERROR'}")
    for line in lines:
        print(f"  {line}")
    print(bar)


def start_runner(env_file: Path, *, self_check_only: bool = False) -> int:
    runner_dir = env_file.parent
    pid_file = runner_dir / "worker.pid"
    stop_signal = runner_dir / "stop.signal"
    log_file = runner_dir / "worker.log"
    err_file = runner_dir / "worker.err.log"

    print("Starting ThinkFirst Local Judge0 Code Runner...")
    cfg = _read_env(env_file)
    j0_token = cfg.get("JUDGE0_AUTH_TOKEN", "").strip()
    worker_token = cfg.get("EXECUTION_WORKER_TOKEN", "").strip()
    worker_id = cfg.get("EXECUTION_WORKER_ID", "win-runner").strip()
    api_base = cfg.get(
        "THINKFIRST_API_BASE_URL", "https://codementor-ai-backend-6sbr.onrender.com"
    ).strip()
    j0_base = cfg.get("JUDGE0_BASE_URL", "http://127.0.0.1:2359").strip()

    if not j0_token or not worker_token:
        raise RuntimeError(f"Missing JUDGE0_AUTH_TOKEN or EXECUTION_WORKER_TOKEN in {env_file}.")

    # 1. Check Docker Desktop
    print("[1/6] Checking Docker Desktop...")
    dinfo = subprocess.run(["docker", "info"], capture_output=True, text=True, check=False)
    if dinfo.returncode != 0:
        raise RuntimeError(
            "Docker Desktop is not running. Please open Docker Desktop and wait until ready."
        )

    # 2. Verify Judge0 PostgreSQL, Redis, Server, and Workers (never delete volumes)
    print("[2/6] Verifying Judge0 PostgreSQL, Redis, Server, and Workers...")
    required = [
        "think_first-judge0-db-1",
        "think_first-judge0-redis-1",
        "think_first-judge0-server-1",
        "think_first-judge0-workers-1",
    ]
    ps_out = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    missing = [c for c in required if c not in ps_out]
    if missing:
        print(f"      Starting Judge0 containers: {', '.join(missing)}...")
        comp_env = os.environ.copy()
        comp_env["JUDGE0_AUTH_TOKEN"] = j0_token
        up = subprocess.run(
            [
                "docker",
                "compose",
                "--profile",
                "execution",
                "up",
                "-d",
                "judge0-db",
                "judge0-redis",
                "judge0-server",
                "judge0-workers",
            ],
            cwd=str(_REPO_ROOT),
            env=comp_env,
            capture_output=True,
            text=True,
            check=False,
        )
        if up.returncode != 0:
            raise RuntimeError(f"Failed to start Judge0 containers: {up.stderr.strip()}")

    pg_chk = subprocess.run(
        ["docker", "exec", "think_first-judge0-db-1", "pg_isready", "-U", "judge0", "-d", "judge0"],
        capture_output=True,
        text=True,
        check=False,
    )
    if pg_chk.returncode != 0:
        raise RuntimeError(f"Judge0 PostgreSQL is not ready: {pg_chk.stdout} {pg_chk.stderr}")

    redis_chk = subprocess.run(
        [
            "docker",
            "exec",
            "think_first-judge0-redis-1",
            "sh",
            "-c",
            'REDISCLI_AUTH="${JUDGE0_REDIS_PASSWORD:-judge0_dev_redis}" redis-cli ping',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if redis_chk.returncode != 0 or "PONG" not in (redis_chk.stdout or ""):
        raise RuntimeError(f"Judge0 Redis is not healthy: {redis_chk.stdout} {redis_chk.stderr}")

    port_bind = subprocess.run(
        [
            "docker",
            "inspect",
            "think_first-judge0-server-1",
            "--format",
            "{{json .HostConfig.PortBindings}}",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    if '"HostIp":"127.0.0.1"' not in port_bind:
        raise RuntimeError("Security check failed: judge0-server is not bound to 127.0.0.1.")

    # 3. Verify local Judge0 auth & readiness
    print(f"[3/6] Verifying local Judge0 authentication and readiness ({j0_base})...")
    ready = False
    with httpx.Client(timeout=5.0) as client:
        for _ in range(20):
            try:
                r = client.get(f"{j0_base}/config_info", headers={"X-Auth-Token": j0_token})
                if r.status_code == 200:
                    ready = True
                    break
            except Exception:
                pass
            time.sleep(1.0)
        if not ready:
            raise RuntimeError(
                "Local Judge0 did not respond HTTP 200 with configured X-Auth-Token."
            )

        unauth = client.get(f"{j0_base}/config_info")
        if unauth.status_code != 401:
            raise RuntimeError(
                "Security check failed: local Judge0 allowed unauthenticated request "
                f"({unauth.status_code})."
            )

    # 4. Verify worker authentication & production execution queue access
    print(f"[4/6] Verifying outbound worker authentication against {api_base}...")
    worker = OutboundExecutionWorker(
        api_base_url=api_base,
        worker_id=worker_id,
        worker_token=worker_token,
        judge0_base_url=j0_base,
        judge0_auth_token=j0_token,
    )
    asyncio.run(worker.self_check())
    print("      READY: Local Judge0 and production execution queue verified.")

    if self_check_only:
        _print_banner(True, ["Self-check completed cleanly."])
        return 0

    # 5. Start outbound worker safely (or confirm already running)
    print("[5/6] Starting outbound local execution worker...")
    stop_signal.unlink(missing_ok=True)
    if pid_file.exists():
        raw_pid = pid_file.read_text(encoding="utf-8").strip()
        if raw_pid.isdigit() and _is_pid_running(int(raw_pid)):
            _print_banner(
                True,
                [
                    f"Worker PID  : {raw_pid} (already running)",
                    f"Local Judge0: {j0_base} (127.0.0.1 authenticated)",
                    f"Production  : {api_base} (outbound HTTPS only)",
                ],
            )
            return 0
        pid_file.unlink(missing_ok=True)

    worker_script = _BACKEND_DIR / "worker" / "execution_worker.py"
    with log_file.open("ab") as out_fh, err_file.open("ab") as err_fh:
        creation_flags = _windows_detached_creation_flags()
        proc = subprocess.Popen(
            [sys.executable, str(worker_script), "--env-file", str(env_file)],
            cwd=str(_BACKEND_DIR),
            stdin=subprocess.DEVNULL,
            stdout=out_fh,
            stderr=err_fh,
            creationflags=creation_flags,
            close_fds=True,
        )

    pid_file.write_text(str(proc.pid), encoding="ascii")

    # 6. Verify process stability
    print("[6/6] Confirming worker process stability...")
    time.sleep(2.0)
    if not _is_pid_running(proc.pid):
        pid_file.unlink(missing_ok=True)
        err_tail = err_file.read_text(encoding="utf-8", errors="replace")[-400:]
        raise RuntimeError(f"Worker exited immediately after startup. {err_tail}")

    _print_banner(
        True,
        [
            f"Worker PID  : {proc.pid}",
            f"Local Judge0: {j0_base} (127.0.0.1 authenticated)",
            f"Production  : {api_base} (outbound HTTPS only)",
            f"Logs        : {log_file}",
            "Stop command: .\\STOP_THINKFIRST_CODE_RUNNER.ps1",
        ],
    )
    return 0


def stop_runner(env_file: Path) -> int:
    runner_dir = env_file.parent
    pid_file = runner_dir / "worker.pid"
    stop_signal = runner_dir / "stop.signal"

    print("Stopping ThinkFirst Local Judge0 Code Runner...")
    if not pid_file.exists():
        stop_signal.unlink(missing_ok=True)
        print("No active worker PID file found. Docker volumes and containers preserved untouched.")
        return 0

    raw_pid = pid_file.read_text(encoding="utf-8").strip()
    if not raw_pid.isdigit():
        pid_file.unlink(missing_ok=True)
        stop_signal.unlink(missing_ok=True)
        return 0

    pid = int(raw_pid)
    if not _is_pid_running(pid):
        pid_file.unlink(missing_ok=True)
        stop_signal.unlink(missing_ok=True)
        print(f"Worker PID {pid} is already stopped.")
        return 0

    stop_signal.write_text("stop\n", encoding="ascii")
    print(
        f"Sent graceful stop signal to worker PID {pid} (waiting up to 20s for in-flight jobs)..."
    )
    for _ in range(20):
        time.sleep(1.0)
        if not _is_pid_running(pid):
            break
    else:
        print(f"Worker did not exit within 20s; terminating worker PID {pid} only...")
        _stop_pid_force(pid)
        time.sleep(1.0)

    pid_file.unlink(missing_ok=True)
    stop_signal.unlink(missing_ok=True)
    print("")
    print("=" * 60)
    print("  THINKFIRST CODE RUNNER STATUS: STOPPED SAFELY")
    print("  All Docker containers and volumes were preserved untouched.")
    print("=" * 60)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ThinkFirst Local Judge0 Code Runner Controller")
    parser.add_argument("action", choices=["start", "stop", "self-check"])
    parser.add_argument("--env-file", type=Path, default=_default_env_path())
    args = parser.parse_args()
    try:
        if args.action == "start":
            return start_runner(args.env_file, self_check_only=False)
        if args.action == "self-check":
            return start_runner(args.env_file, self_check_only=True)
        return stop_runner(args.env_file)
    except Exception as exc:
        _print_banner(False, [str(exc)])
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
