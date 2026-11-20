"""Phase 9 local PostgreSQL backup & disposable-database restore verification script."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

CRITICAL_TABLES = (
    "profiles",
    "user_roles",
    "learning_tracks",
    "skill_nodes",
    "lessons",
    "problems",
    "diagnostic_questions",
    "knowledge_documents",
    "courses",
    "assignments",
    "submissions",
    "learning_events",
    "audit_logs",
)


def _run(cmd: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        check=False,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if proc.returncode != 0:
        if capture and proc.stderr:
            print(proc.stderr[-1200:], file=sys.stderr)
        raise subprocess.CalledProcessError(proc.returncode, cmd, proc.stdout, proc.stderr)
    return proc


def _query_counts_via_docker(container: str, dbname: str) -> dict[str, int]:
    select_parts = [
        f"SELECT '{tbl}' AS tbl, count(*) AS cnt FROM public.{tbl}" for tbl in CRITICAL_TABLES
    ]
    sql = " UNION ALL ".join(select_parts) + ";"
    proc = _run(
        [
            "docker",
            "exec",
            container,
            "psql",
            "-U",
            "postgres",
            "-d",
            dbname,
            "-At",
            "-F",
            "|",
            "-c",
            sql,
        ],
        capture=True,
    )
    counts: dict[str, int] = {}
    for line in proc.stdout.strip().splitlines():
        if "|" in line:
            tbl, raw_cnt = line.split("|", 1)
            counts[tbl.strip()] = int(raw_cnt.strip())
    return counts


def _verify_rls_count_via_docker(container: str, dbname: str) -> tuple[int, int]:
    sql = (
        "SELECT count(*), count(*) FILTER (WHERE relrowsecurity AND relforcerowsecurity) "
        "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relkind = 'r';"
    )
    proc = _run(
        [
            "docker",
            "exec",
            container,
            "psql",
            "-U",
            "postgres",
            "-d",
            dbname,
            "-At",
            "-F",
            "|",
            "-c",
            sql,
        ],
        capture=True,
    )
    line = proc.stdout.strip().splitlines()[-1]
    total_str, rls_str = line.split("|", 1)
    return int(total_str.strip()), int(rls_str.strip())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify backup dump and disposable restore parity for Think_First."
    )
    parser.add_argument(
        "--container",
        default=os.environ.get("SUPABASE_DB_CONTAINER", "supabase_db_think-first-codementor"),
    )
    parser.add_argument("--source-db", default="postgres")
    parser.add_argument("--temp-db", default="thinkfirst_backup_verify_tmp")
    args = parser.parse_args()

    source_counts = _query_counts_via_docker(args.container, args.source_db)
    total_tables, rls_tables = _verify_rls_count_via_docker(args.container, args.source_db)
    print(f"[source] public_tables={total_tables} force_rls_tables={rls_tables}")

    with tempfile.TemporaryDirectory(prefix="thinkfirst_bak_") as tmp_dir:
        dump_host_path = Path(tmp_dir) / "public_backup.sql"
        dump_container_path = "/tmp/thinkfirst_public_backup.sql"

        try:
            _run(
                [
                    "docker",
                    "exec",
                    args.container,
                    "pg_dump",
                    "-U",
                    "postgres",
                    "-d",
                    args.source_db,
                    "--schema=auth",
                    "--schema=public",
                    "--no-owner",
                    "--no-privileges",
                    "-f",
                    dump_container_path,
                ]
            )
            _run(
                [
                    "docker",
                    "cp",
                    f"{args.container}:{dump_container_path}",
                    str(dump_host_path),
                ]
            )
            dump_bytes = dump_host_path.stat().st_size
            print(f"[dump] size_bytes={dump_bytes}")

            _run(
                [
                    "docker",
                    "exec",
                    args.container,
                    "psql",
                    "-U",
                    "postgres",
                    "-d",
                    "postgres",
                    "-c",
                    f"DROP DATABASE IF EXISTS {args.temp_db};",
                ]
            )
            _run(
                [
                    "docker",
                    "exec",
                    args.container,
                    "psql",
                    "-U",
                    "postgres",
                    "-d",
                    "postgres",
                    "-c",
                    f"CREATE DATABASE {args.temp_db};",
                ]
            )
            # Prepare required extensions cleanly and preserve pre-installed public.vector
            _run(
                [
                    "docker",
                    "exec",
                    args.container,
                    "psql",
                    "-U",
                    "postgres",
                    "-d",
                    args.temp_db,
                    "-c",
                    (
                        "CREATE SCHEMA IF NOT EXISTS extensions; "
                        "CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions; "
                        "CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;"
                    ),
                ]
            )
            _run(
                [
                    "docker",
                    "exec",
                    args.container,
                    "sed",
                    "-i",
                    "s/^CREATE SCHEMA public;/CREATE SCHEMA IF NOT EXISTS public;/",
                    dump_container_path,
                ]
            )
            _run(
                [
                    "docker",
                    "exec",
                    args.container,
                    "psql",
                    "-U",
                    "postgres",
                    "-d",
                    args.temp_db,
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-f",
                    dump_container_path,
                ],
                capture=True,
            )

            restored_counts = _query_counts_via_docker(args.container, args.temp_db)
            mismatches = [
                (tbl, source_counts[tbl], restored_counts.get(tbl))
                for tbl in CRITICAL_TABLES
                if source_counts[tbl] != restored_counts.get(tbl)
            ]
            if mismatches:
                print(f"[FAIL] Restored row count mismatch: {mismatches}", file=sys.stderr)
                return 1

            r_total, r_rls = _verify_rls_count_via_docker(args.container, args.temp_db)
            if (r_total, r_rls) != (total_tables, rls_tables):
                print(
                    f"[FAIL] RLS mismatch: source=({total_tables},{rls_tables}) "
                    f"restored=({r_total},{r_rls})",
                    file=sys.stderr,
                )
                return 1

            print(
                f"[PASS] Restored {r_total} tables ({r_rls} with FORCE RLS), "
                f"all {len(CRITICAL_TABLES)} critical tables matched 100%: {restored_counts}"
            )
        finally:
            subprocess.run(
                [
                    "docker",
                    "exec",
                    args.container,
                    "psql",
                    "-U",
                    "postgres",
                    "-d",
                    "postgres",
                    "-c",
                    f"DROP DATABASE IF EXISTS {args.temp_db};",
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["docker", "exec", args.container, "rm", "-f", dump_container_path],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
