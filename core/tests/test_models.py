from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from core.models import DailySheet, UserPreferences, WorkSession


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        username="morgan",
        password="calm-focus-123",
    )


def test_for_user_returns_existing_preferences_after_integrity_error(user) -> None:
    existing_preferences = UserPreferences.objects.create(user=user)

    with patch.object(
        UserPreferences.objects,
        "get_or_create",
        side_effect=IntegrityError("duplicate key value violates unique constraint"),
    ):
        preferences = UserPreferences.for_user(user)

    assert preferences == existing_preferences


def test_daily_sheet_create_adds_default_work_sessions(user) -> None:
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))

    sessions = list(sheet.work_sessions.order_by("slot"))

    assert [session.slot for session in sessions] == [
        WorkSession.Slot.PERSONAL_1,
        WorkSession.Slot.PERSONAL_2,
        WorkSession.Slot.PERSONAL_3,
        WorkSession.Slot.ADMIN,
    ]
    assert [session.category for session in sessions] == [
        WorkSession.Category.PERSONAL,
        WorkSession.Category.PERSONAL,
        WorkSession.Category.PERSONAL,
        WorkSession.Category.ADMIN,
    ]
    assert all(session.status == WorkSession.Status.PLANNED for session in sessions)
    assert all(session.goal == "" for session in sessions)
    assert all(session.notes == "" for session in sessions)
    assert all(session.started_at is None for session in sessions)
    assert all(session.completed_at is None for session in sessions)
    assert all(session.skipped_at is None for session in sessions)


def test_daily_sheet_requires_unique_date_per_user(user) -> None:
    DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))

    with pytest.raises(IntegrityError):
        DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))


def test_daily_sheet_allows_same_date_for_different_users(user) -> None:
    other_user = get_user_model().objects.create_user(
        username="riley",
        password="calm-focus-123",
    )

    first_sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))
    second_sheet = DailySheet.objects.create(
        user=other_user,
        sheet_date=date(2026, 4, 1),
    )

    assert first_sheet.pk != second_sheet.pk


def test_daily_sheet_save_preserves_fixed_session_structure(user) -> None:
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))

    sheet.save()

    assert sheet.work_sessions.count() == 4


def test_work_session_rejects_duplicate_slot_for_daily_sheet(user) -> None:
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))

    with pytest.raises(ValidationError):
        WorkSession.objects.create(
            daily_sheet=sheet,
            slot=WorkSession.Slot.PERSONAL_1,
            category=WorkSession.Category.PERSONAL,
        )


def test_work_session_rejects_mismatched_category_for_slot(user) -> None:
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))
    session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1)
    session.category = WorkSession.Category.ADMIN

    with pytest.raises(
        ValidationError,
        match="Personal 1 must use the personal category",
    ):
        session.save()


def test_work_session_persists_goal_status_and_timer_fields(user) -> None:
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))
    session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_2)
    started_at = timezone.now()

    session.goal = "Write the project outline"
    session.notes = "Stay offline and finish the first draft."
    session.status = WorkSession.Status.ACTIVE
    session.started_at = started_at
    session.save()
    session.refresh_from_db()

    assert session.goal == "Write the project outline"
    assert session.notes == "Stay offline and finish the first draft."
    assert session.status == WorkSession.Status.ACTIVE
    assert session.started_at == started_at
    assert session.completed_at is None
    assert session.skipped_at is None


def test_work_session_cannot_be_deleted_individually(user) -> None:
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))
    session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1)

    with pytest.raises(ValidationError, match="cannot be deleted individually"):
        session.delete()

    with pytest.raises(ValidationError, match="cannot be deleted individually"):
        sheet.work_sessions.all().delete()


def test_deleting_daily_sheet_cascades_to_work_sessions(user) -> None:
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))
    session_ids = list(sheet.work_sessions.values_list("id", flat=True))

    sheet.delete()

    assert WorkSession.objects.filter(id__in=session_ids).count() == 0


def test_daily_sheet_string_representation(user) -> None:
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))

    assert str(sheet) == "morgan - 2026-04-01"


def test_work_session_string_representation(user) -> None:
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))
    session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1)

    assert str(session) == "morgan - 2026-04-01 - Personal 1"
