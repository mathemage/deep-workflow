import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.utils import OperationalError


def test_check_database_command_reports_success(capsys, db) -> None:
    call_command("check_database")

    captured = capsys.readouterr()
    assert "Database readiness check passed." in captured.out


def test_check_database_command_raises_command_error_on_database_failure(
    monkeypatch,
) -> None:
    def fail_database_check() -> str:
        raise OperationalError("database unavailable")

    monkeypatch.setattr(
        "core.management.commands.check_database.check_database",
        fail_database_check,
    )

    error_message = (
        "Database readiness check failed. Verify DATABASE_URL, credentials, "
        "network access, and database availability before deploying."
    )

    with pytest.raises(CommandError, match=error_message):
        call_command("check_database")
