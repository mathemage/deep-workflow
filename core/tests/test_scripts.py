import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_URL = "sqlite:////tmp/deep-workflow.sqlite3"
TARGET_URL = "postgresql://admin.example/deep_workflow"
RUNTIME_URL = "postgresql://runtime.example/deep_workflow"


def write_fake_python(tmp_path: Path) -> Path:
    fake_python = tmp_path / "python"
    fake_python.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'printf \'%s|%s\\n\' "${DATABASE_URL:-}" "$*" >> "$COMMAND_LOG"\n'
        'if [[ "${2:-}" == "dumpdata" ]]; then\n'
        "  printf '[]'\n"
        "fi\n"
    )
    fake_python.chmod(0o755)
    return fake_python


def run_script(
    tmp_path: Path,
    script_name: str,
    *,
    extra_env: dict[str, str],
) -> list[str]:
    write_fake_python(tmp_path)
    command_log = tmp_path / "commands.log"
    env = os.environ.copy()
    env.update(extra_env)
    env["COMMAND_LOG"] = str(command_log)
    env["PATH"] = f"{tmp_path}:{env['PATH']}"
    subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / script_name)],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return command_log.read_text().splitlines()


def test_vercel_build_uses_runtime_database_for_checks_and_admin_url_for_migrate(
    tmp_path: Path,
) -> None:
    commands = run_script(
        tmp_path,
        "vercel-build.sh",
        extra_env={
            "VERCEL_ENV": "production",
            "VERCEL": "1",
            "DJANGO_SECRET_KEY": "x" * 64,
            "DATABASE_URL": RUNTIME_URL,
            "DATABASE_ADMIN_URL": TARGET_URL,
            "VERCEL_RUN_MIGRATIONS": "1",
        },
    )

    assert commands == [
        f"{RUNTIME_URL}|manage.py check_database",
        f"{RUNTIME_URL}|manage.py collectstatic --noinput",
        f"{TARGET_URL}|manage.py check_database",
        f"{TARGET_URL}|manage.py migrate --noinput",
    ]


def test_vercel_build_uses_runtime_database_for_migrate_without_admin_url(
    tmp_path: Path,
) -> None:
    commands = run_script(
        tmp_path,
        "vercel-build.sh",
        extra_env={
            "VERCEL_ENV": "production",
            "VERCEL": "1",
            "DJANGO_SECRET_KEY": "x" * 64,
            "DATABASE_URL": RUNTIME_URL,
            "VERCEL_RUN_MIGRATIONS": "1",
        },
    )

    assert commands == [
        f"{RUNTIME_URL}|manage.py check_database",
        f"{RUNTIME_URL}|manage.py collectstatic --noinput",
        f"{RUNTIME_URL}|manage.py migrate --noinput",
    ]


def test_transfer_django_data_moves_data_between_source_and_target_urls(
    tmp_path: Path,
) -> None:
    commands = run_script(
        tmp_path,
        "transfer-django-data.sh",
        extra_env={
            "SOURCE_DATABASE_URL": SOURCE_URL,
            "TARGET_DATABASE_URL": TARGET_URL,
        },
    )

    assert commands[0] == f"{SOURCE_URL}|manage.py check_database"
    assert commands[1] == (
        f"{SOURCE_URL}|manage.py dumpdata --exclude admin.logentry "
        "--exclude auth.permission --exclude contenttypes --exclude "
        "sessions --natural-foreign --natural-primary"
    )
    assert commands[2] == f"{TARGET_URL}|manage.py check_database"
    assert commands[3] == f"{TARGET_URL}|manage.py migrate --noinput"
    assert commands[4].startswith(
        f"{TARGET_URL}|manage.py loaddata /tmp/deep-workflow-transfer."
    )
