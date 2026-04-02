from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

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
    assert all(session.duration_minutes == 45 for session in sessions)
    assert all(session.started_at is None for session in sessions)
    assert all(session.active_started_at is None for session in sessions)
    assert all(session.elapsed_seconds == 0 for session in sessions)
    assert all(session.completed_at is None for session in sessions)
    assert all(session.skipped_at is None for session in sessions)


def test_daily_sheet_uses_user_default_session_duration_for_new_sessions(user) -> None:
    UserPreferences.objects.create(
        user=user,
        default_session_duration_minutes=60,
    )

    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 2))

    assert all(session.duration_minutes == 60 for session in sheet.work_sessions.all())


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
    started_at = datetime(2026, 4, 1, 9, 0, tzinfo=dt_timezone.utc)

    session.goal = "Write the project outline"
    session.notes = "Stay offline and finish the first draft."
    session.status = WorkSession.Status.ACTIVE
    session.duration_minutes = 50
    session.started_at = started_at
    session.active_started_at = started_at
    session.elapsed_seconds = 120
    session.save()
    session.refresh_from_db()

    assert session.goal == "Write the project outline"
    assert session.notes == "Stay offline and finish the first draft."
    assert session.status == WorkSession.Status.ACTIVE
    assert session.duration_minutes == 50
    assert session.started_at == started_at
    assert session.active_started_at == started_at
    assert session.elapsed_seconds == 120
    assert session.completed_at is None
    assert session.skipped_at is None


def test_work_session_start_sets_initial_timer_fields(user) -> None:
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))
    session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1)
    start_time = datetime(2026, 4, 1, 9, 0, tzinfo=dt_timezone.utc)

    session.start(now=start_time)
    session.refresh_from_db()

    assert session.status == WorkSession.Status.ACTIVE
    assert session.started_at == start_time
    assert session.active_started_at == start_time
    assert session.elapsed_seconds == 0
    assert session.completed_at is None
    assert session.skipped_at is None


def test_work_session_pause_resume_and_complete_preserve_elapsed_time(user) -> None:
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))
    session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1)
    start_time = datetime(2026, 4, 1, 9, 0, tzinfo=dt_timezone.utc)
    pause_time = start_time + timedelta(minutes=10)
    resume_time = pause_time + timedelta(minutes=5)
    complete_time = resume_time + timedelta(minutes=20)

    session.start(now=start_time)
    session.pause(now=pause_time)
    session.refresh_from_db()

    assert session.status == WorkSession.Status.PAUSED
    assert session.started_at == start_time
    assert session.active_started_at is None
    assert session.elapsed_seconds == 600
    assert session.remaining_seconds(now=pause_time) == 2100

    session.resume(now=resume_time)
    session.refresh_from_db()

    assert session.status == WorkSession.Status.ACTIVE
    assert session.active_started_at == resume_time
    assert session.elapsed_seconds == 600

    session.complete(now=complete_time)
    session.refresh_from_db()

    assert session.status == WorkSession.Status.COMPLETED
    assert session.started_at == start_time
    assert session.active_started_at is None
    assert session.elapsed_seconds == 1800
    assert session.completed_at == complete_time
    assert session.remaining_seconds(now=complete_time) == 900


def test_work_session_remaining_seconds_clamps_at_zero(user) -> None:
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))
    session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_3)
    start_time = datetime(2026, 4, 1, 9, 0, tzinfo=dt_timezone.utc)

    session.start(now=start_time)

    assert session.remaining_seconds(now=start_time + timedelta(minutes=50)) == 0


def test_work_session_rejects_invalid_timer_transitions(user) -> None:
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))
    session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1)
    start_time = datetime(2026, 4, 1, 9, 0, tzinfo=dt_timezone.utc)

    with pytest.raises(ValidationError, match="Only active sessions can be paused."):
        session.pause(now=start_time)

    with pytest.raises(
        ValidationError,
        match="Only active or paused sessions can be completed.",
    ):
        session.complete(now=start_time)

    session.start(now=start_time)

    with pytest.raises(ValidationError, match="Only planned sessions can be started."):
        session.start(now=start_time)

    with pytest.raises(ValidationError, match="Only paused sessions can be resumed."):
        session.resume(now=start_time)

    with pytest.raises(ValidationError, match="Only planned sessions can be skipped."):
        session.skip(now=start_time)


def test_work_session_prevents_second_active_session_for_same_user(user) -> None:
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))
    first_session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1)
    second_session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_2)
    start_time = datetime(2026, 4, 1, 9, 0, tzinfo=dt_timezone.utc)

    first_session.start(now=start_time)

    with pytest.raises(
        ValidationError,
        match="Pause or complete the other active session before starting this one.",
    ):
        second_session.start(now=start_time + timedelta(minutes=1))


def test_work_session_skip_and_mark_planned_reset_timer_fields(user) -> None:
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 1))
    session = sheet.work_sessions.get(slot=WorkSession.Slot.ADMIN)
    skipped_time = datetime(2026, 4, 1, 9, 30, tzinfo=dt_timezone.utc)

    session.skip(now=skipped_time)
    session.refresh_from_db()

    assert session.status == WorkSession.Status.SKIPPED
    assert session.skipped_at == skipped_time
    assert session.started_at is None
    assert session.active_started_at is None
    assert session.elapsed_seconds == 0

    session.mark_planned()
    session.refresh_from_db()

    assert session.status == WorkSession.Status.PLANNED
    assert session.skipped_at is None
    assert session.elapsed_seconds == 0


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
