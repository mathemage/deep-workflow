from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from pytest_django.asserts import assertContains, assertTemplateUsed

from core.models import DailySheet, UserPreferences, WorkSession
from core.views import completion_percentage


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        username="jules",
        password="calm-focus-123",
    )


def complete_session(session: WorkSession, *, start_time: datetime) -> None:
    session.start(now=start_time)
    session.complete(now=start_time + timedelta(minutes=session.duration_minutes))


def test_completion_percentage_uses_round_half_up() -> None:
    assert completion_percentage(1, 8) == 13


def test_completion_percentage_clamps_to_0_and_100() -> None:
    assert completion_percentage(-1, 4) == 0
    assert completion_percentage(5, 4) == 100


def test_home_renders_daily_sheet_for_today(client, user) -> None:
    client.force_login(user)

    response = client.get(reverse("home"))

    assert response.status_code == 200
    assertTemplateUsed(response, "core/home.html")
    assert response.context["is_today"] is True
    assert UserPreferences.objects.filter(user=user).exists()
    assert DailySheet.objects.filter(
        user=user,
        sheet_date=response.context["selected_date"],
    ).exists()
    assert [card["session"].slot for card in response.context["session_cards"]] == [
        WorkSession.Slot.PERSONAL_1,
        WorkSession.Slot.PERSONAL_2,
        WorkSession.Slot.PERSONAL_3,
        WorkSession.Slot.ADMIN,
    ]
    assertContains(response, "Personal 1")
    assertContains(response, "Admin")
    assertContains(response, "Previous day")
    assertContains(response, "Next day")
    assertContains(response, "completed today")


def test_home_uses_user_timezone_to_pick_todays_sheet(client, user) -> None:
    UserPreferences.objects.create(user=user, timezone="America/Los_Angeles")
    client.force_login(user)
    current_time = datetime(2026, 4, 6, 6, 30, tzinfo=dt_timezone.utc)

    with patch("core.views.timezone.now", return_value=current_time):
        response = client.get(reverse("home"))

    assert response.status_code == 200
    assert response.context["selected_date"] == date(2026, 4, 5)
    assert DailySheet.objects.filter(user=user, sheet_date=date(2026, 4, 5)).exists()
    assert not DailySheet.objects.filter(
        user=user,
        sheet_date=date(2026, 4, 6),
    ).exists()


def test_home_loads_selected_day_and_navigation(client, user) -> None:
    client.force_login(user)
    selected_date = date(2026, 4, 5)

    response = client.get(reverse("home"), {"date": selected_date.isoformat()})

    assert response.status_code == 200
    assert response.context["selected_date"] == selected_date
    assert response.context["previous_date"] == date(2026, 4, 4)
    assert response.context["next_date"] == date(2026, 4, 6)
    assert response.context["is_today"] is False
    assert DailySheet.objects.filter(user=user, sheet_date=selected_date).exists()
    assertContains(response, "?date=2026-04-04")
    assertContains(response, "?date=2026-04-06")
    assertContains(response, "completed on this day")


def test_home_strips_whitespace_from_selected_day(client, user) -> None:
    client.force_login(user)

    response = client.get(reverse("home"), {"date": "2026-04-05 "})

    assert response.status_code == 200
    assert response.context["selected_date"] == date(2026, 4, 5)


def test_home_rejects_invalid_selected_day(client, user) -> None:
    client.force_login(user)

    response = client.get(reverse("home"), {"date": "not-a-date"})

    assert response.status_code == 404


def test_home_repairs_missing_default_session_structure(client, user) -> None:
    selected_date = date(2026, 4, 5)
    DailySheet.objects.bulk_create([DailySheet(user=user, sheet_date=selected_date)])
    sheet = DailySheet.objects.get(user=user, sheet_date=selected_date)
    client.force_login(user)

    assert sheet.work_sessions.count() == 0

    response = client.get(reverse("home"), {"date": selected_date.isoformat()})

    assert response.status_code == 200
    assert [card["session"].slot for card in response.context["session_cards"]] == [
        WorkSession.Slot.PERSONAL_1,
        WorkSession.Slot.PERSONAL_2,
        WorkSession.Slot.PERSONAL_3,
        WorkSession.Slot.ADMIN,
    ]
    repaired_sheet = DailySheet.objects.get(user=user, sheet_date=selected_date)
    assert repaired_sheet.work_sessions.count() == 4


def test_home_skips_slot_repair_queries_when_structure_is_already_healthy(
    client,
    user,
) -> None:
    client.force_login(user)
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 5))

    with patch.object(
        DailySheet,
        "ensure_default_work_sessions",
        side_effect=AssertionError("Healthy sheets should not need slot repair."),
    ):
        response = client.get(reverse("home"), {"date": sheet.sheet_date.isoformat()})

    assert response.status_code == 200


def test_home_builds_daily_and_weekly_completion_summaries(client, user) -> None:
    client.force_login(user)
    selected_date = date(2026, 4, 8)

    monday_sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 6))
    tuesday_sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 7))
    wednesday_sheet = DailySheet.objects.create(user=user, sheet_date=selected_date)

    monday_start = datetime(2026, 4, 6, 9, 0, tzinfo=dt_timezone.utc)
    for index, session in enumerate(monday_sheet.work_sessions.order_by("slot")):
        complete_session(
            session,
            start_time=monday_start + timedelta(hours=index),
        )

    complete_session(
        tuesday_sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1),
        start_time=datetime(2026, 4, 7, 9, 0, tzinfo=dt_timezone.utc),
    )
    complete_session(
        wednesday_sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1),
        start_time=datetime(2026, 4, 8, 9, 0, tzinfo=dt_timezone.utc),
    )
    complete_session(
        wednesday_sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_2),
        start_time=datetime(2026, 4, 8, 10, 0, tzinfo=dt_timezone.utc),
    )

    response = client.get(reverse("home"), {"date": selected_date.isoformat()})

    assert response.status_code == 200
    assertContains(response, "Daily completion")
    assertContains(response, "Weekly completion")
    assertContains(response, "Consistency")
    assert response.context["daily_summary"] == {
        "total_sessions": 4,
        "completed_sessions": 2,
        "completion_percentage": 50,
        "in_progress_sessions": 0,
        "open_sessions": 2,
        "skipped_sessions": 0,
    }
    assert response.context["weekly_summary"] == {
        "week_start": date(2026, 4, 6),
        "week_end": date(2026, 4, 12),
        "completed_sessions": 7,
        "total_sessions": 28,
        "completion_percentage": 25,
        "focused_days": 3,
        "completed_days": 1,
        "streak_days": 3,
    }


def test_home_streak_breaks_when_the_previous_day_has_no_completed_sessions(
    client,
    user,
) -> None:
    client.force_login(user)
    selected_date = date(2026, 4, 8)
    monday_sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 6))
    wednesday_sheet = DailySheet.objects.create(user=user, sheet_date=selected_date)

    complete_session(
        monday_sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1),
        start_time=datetime(2026, 4, 6, 9, 0, tzinfo=dt_timezone.utc),
    )
    complete_session(
        wednesday_sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1),
        start_time=datetime(2026, 4, 8, 9, 0, tzinfo=dt_timezone.utc),
    )

    response = client.get(reverse("home"), {"date": selected_date.isoformat()})

    assert response.status_code == 200
    assert response.context["weekly_summary"]["streak_days"] == 1


def test_home_streak_extends_before_the_current_week(client, user) -> None:
    client.force_login(user)
    selected_date = date(2026, 4, 8)
    sunday_sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 5))
    monday_sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 6))
    tuesday_sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 7))
    wednesday_sheet = DailySheet.objects.create(user=user, sheet_date=selected_date)

    complete_session(
        sunday_sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1),
        start_time=datetime(2026, 4, 5, 9, 0, tzinfo=dt_timezone.utc),
    )
    complete_session(
        monday_sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1),
        start_time=datetime(2026, 4, 6, 9, 0, tzinfo=dt_timezone.utc),
    )
    complete_session(
        tuesday_sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1),
        start_time=datetime(2026, 4, 7, 9, 0, tzinfo=dt_timezone.utc),
    )
    complete_session(
        wednesday_sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1),
        start_time=datetime(2026, 4, 8, 9, 0, tzinfo=dt_timezone.utc),
    )

    response = client.get(reverse("home"), {"date": selected_date.isoformat()})

    assert response.status_code == 200
    assert response.context["weekly_summary"]["streak_days"] == 4


def test_home_streak_avoids_older_history_query_when_gap_is_in_current_week(
    client,
    user,
) -> None:
    client.force_login(user)
    selected_date = date(2026, 4, 8)
    monday_sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 6))
    wednesday_sheet = DailySheet.objects.create(user=user, sheet_date=selected_date)

    complete_session(
        monday_sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1),
        start_time=datetime(2026, 4, 6, 9, 0, tzinfo=dt_timezone.utc),
    )
    complete_session(
        wednesday_sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1),
        start_time=datetime(2026, 4, 8, 9, 0, tzinfo=dt_timezone.utc),
    )

    with patch(
        "core.views.completed_sheet_dates_desc",
        side_effect=AssertionError(
            "A current-week gap should end the streak without older history work."
        ),
    ):
        response = client.get(reverse("home"), {"date": selected_date.isoformat()})

    assert response.status_code == 200
    assert response.context["weekly_summary"]["streak_days"] == 1


def test_home_updates_work_session_fields(client, user) -> None:
    client.force_login(user)
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 5))
    session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_2)

    response = client.post(
        f"{reverse('home')}?date={sheet.sheet_date.isoformat()}",
        {
            "session_id": str(session.pk),
            f"session-{session.pk}-goal": "Ship the card layout",
            f"session-{session.pk}-notes": "Keep the copy calm and focused.",
        },
        follow=True,
    )

    assert response.status_code == 200
    assertContains(response, "Personal 2 saved.")

    session.refresh_from_db()
    assert session.goal == "Ship the card layout"
    assert session.notes == "Keep the copy calm and focused."
    assert session.status == WorkSession.Status.PLANNED


def test_home_updates_fields_without_clobbering_active_timer_state(
    client,
    user,
) -> None:
    client.force_login(user)
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 5))
    session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_2)
    start_time = datetime(2026, 4, 5, 9, 0, tzinfo=dt_timezone.utc)
    session.start(now=start_time)

    response = client.post(
        f"{reverse('home')}?date={sheet.sheet_date.isoformat()}",
        {
            "session_id": str(session.pk),
            f"session-{session.pk}-goal": "Ship the timer polish",
            f"session-{session.pk}-notes": "Keep the active timer intact.",
        },
        follow=True,
    )

    assert response.status_code == 200
    assertContains(response, "Personal 2 saved.")

    session.refresh_from_db()
    assert session.goal == "Ship the timer polish"
    assert session.notes == "Keep the active timer intact."
    assert session.status == WorkSession.Status.ACTIVE
    assert session.started_at == start_time
    assert session.active_started_at == start_time
    assert session.elapsed_seconds == 0


def test_home_shows_errors_for_invalid_session_update(client, user) -> None:
    client.force_login(user)
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 5))
    session = sheet.work_sessions.get(slot=WorkSession.Slot.ADMIN)

    response = client.post(
        f"{reverse('home')}?date={sheet.sheet_date.isoformat()}",
        {
            "session_id": str(session.pk),
            f"session-{session.pk}-goal": "g" * 256,
            f"session-{session.pk}-notes": "Document the loose ends.",
        },
    )

    assert response.status_code == 200
    session_card = next(
        card
        for card in response.context["session_cards"]
        if card["session"].pk == session.pk
    )
    assert "goal" in session_card["form"].errors

    session.refresh_from_db()
    assert session.goal == ""
    assert session.notes == ""
    assert session.status == WorkSession.Status.PLANNED


def test_home_shows_validation_error_when_save_rejects_session_update(
    client,
    user,
) -> None:
    client.force_login(user)
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 5))
    session = sheet.work_sessions.get(slot=WorkSession.Slot.ADMIN)

    with patch.object(
        WorkSession,
        "save",
        side_effect=ValidationError("Timer state is inconsistent."),
    ):
        response = client.post(
            f"{reverse('home')}?date={sheet.sheet_date.isoformat()}",
            {
                "session_id": str(session.pk),
                f"session-{session.pk}-goal": "Tidy the session card",
                f"session-{session.pk}-notes": "Keep the submitted values visible.",
            },
        )

    assert response.status_code == 200
    assertContains(response, "Timer state is inconsistent.")
    session_card = next(
        card
        for card in response.context["session_cards"]
        if card["session"].pk == session.pk
    )
    assert session_card["form"].non_field_errors()
    assert session_card["form"].is_bound

    session.refresh_from_db()
    assert session.goal == ""
    assert session.notes == ""
    assert session.status == WorkSession.Status.PLANNED


def test_home_cannot_update_another_users_session(client, user) -> None:
    other_user = get_user_model().objects.create_user(
        username="river",
        password="calm-focus-123",
    )
    other_sheet = DailySheet.objects.create(
        user=other_user,
        sheet_date=date(2026, 4, 5),
    )
    other_session = other_sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1)
    client.force_login(user)

    response = client.post(
        reverse("home"),
        {
            "session_id": str(other_session.pk),
            f"session-{other_session.pk}-goal": "Intrude on another account",
            f"session-{other_session.pk}-notes": "This should never work.",
        },
    )

    assert response.status_code == 404


def test_session_timer_actions_start_pause_resume_and_complete(client, user) -> None:
    client.force_login(user)
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 5))
    session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_2)
    start_time = datetime(2026, 4, 5, 9, 0, tzinfo=dt_timezone.utc)
    pause_time = start_time + timedelta(minutes=10)
    resume_time = pause_time + timedelta(minutes=5)
    complete_time = resume_time + timedelta(minutes=20)

    with patch("core.views.timezone.now", return_value=start_time):
        response = client.post(
            reverse("session-timer", args=[session.pk]),
            {"action": "start"},
            follow=True,
        )

    assert response.status_code == 200
    assertContains(response, "Personal 2 started.")
    session.refresh_from_db()
    assert session.status == WorkSession.Status.ACTIVE
    assert session.started_at == start_time
    assert session.active_started_at == start_time

    with patch("core.views.timezone.now", return_value=pause_time):
        response = client.post(
            reverse("session-timer", args=[session.pk]),
            {"action": "pause"},
            follow=True,
        )

    assertContains(response, "Personal 2 paused.")
    session.refresh_from_db()
    assert session.status == WorkSession.Status.PAUSED
    assert session.active_started_at is None
    assert session.elapsed_seconds == 600

    with patch("core.views.timezone.now", return_value=resume_time):
        response = client.post(
            reverse("session-timer", args=[session.pk]),
            {"action": "resume"},
            follow=True,
        )

    assertContains(response, "Personal 2 resumed.")
    session.refresh_from_db()
    assert session.status == WorkSession.Status.ACTIVE
    assert session.active_started_at == resume_time
    assert session.elapsed_seconds == 600

    with patch("core.views.timezone.now", return_value=complete_time):
        response = client.post(
            reverse("session-timer", args=[session.pk]),
            {"action": "complete"},
            follow=True,
        )

    assertContains(response, "Personal 2 completed.")
    session.refresh_from_db()
    assert session.status == WorkSession.Status.COMPLETED
    assert session.completed_at == complete_time
    assert session.elapsed_seconds == 1800


def test_home_shows_active_timer_feedback_and_remaining_time(client, user) -> None:
    client.force_login(user)
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 5))
    session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1)
    start_time = datetime(2026, 4, 5, 9, 0, tzinfo=dt_timezone.utc)
    current_time = start_time + timedelta(minutes=15)

    session.start(now=start_time)

    with patch("core.views.timezone.now", return_value=current_time):
        response = client.get(reverse("home"), {"date": sheet.sheet_date.isoformat()})

    assert response.status_code == 200
    assertContains(response, "Remaining time")
    assertContains(response, "30:00")
    assertContains(response, "Pause timer")
    assertContains(response, 'role="timer"')
    assertContains(response, 'aria-live="polite"')
    assertContains(
        response,
        f'data-server-now="{int(current_time.timestamp() * 1000)}"',
    )


def test_session_timer_action_skip_marks_session_skipped(client, user) -> None:
    client.force_login(user)
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 5))
    session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1)

    response = client.post(
        reverse("session-timer", args=[session.pk]),
        {"action": "skip"},
        follow=True,
    )

    assert response.status_code == 200
    assertContains(response, "Personal 1 marked skipped.")
    session.refresh_from_db()
    assert session.status == WorkSession.Status.SKIPPED


def test_session_timer_action_mark_planned_returns_session_to_planned(
    client,
    user,
) -> None:
    client.force_login(user)
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 5))
    session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_2)
    session.skip()

    response = client.post(
        reverse("session-timer", args=[session.pk]),
        {"action": "mark_planned"},
        follow=True,
    )

    assert response.status_code == 200
    assertContains(response, "Personal 2 moved back to planned.")
    session.refresh_from_db()
    assert session.status == WorkSession.Status.PLANNED


def test_session_timer_rejects_second_active_session_for_user(client, user) -> None:
    client.force_login(user)
    sheet = DailySheet.objects.create(user=user, sheet_date=date(2026, 4, 5))
    active_session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1)
    blocked_session = sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_2)
    start_time = datetime(2026, 4, 5, 9, 0, tzinfo=dt_timezone.utc)

    active_session.start(now=start_time)

    with patch(
        "core.views.timezone.now",
        return_value=start_time + timedelta(minutes=5),
    ):
        response = client.post(
            reverse("session-timer", args=[blocked_session.pk]),
            {"action": "start"},
            follow=True,
        )

    assert response.status_code == 200
    assertContains(
        response,
        "Pause or complete the other active session before starting this one.",
    )
    blocked_session.refresh_from_db()
    assert blocked_session.status == WorkSession.Status.PLANNED


def test_session_timer_cannot_update_another_users_session(client, user) -> None:
    other_user = get_user_model().objects.create_user(
        username="river",
        password="calm-focus-123",
    )
    other_sheet = DailySheet.objects.create(
        user=other_user,
        sheet_date=date(2026, 4, 5),
    )
    other_session = other_sheet.work_sessions.get(slot=WorkSession.Slot.PERSONAL_1)
    client.force_login(user)

    response = client.post(
        reverse("session-timer", args=[other_session.pk]),
        {"action": "start"},
    )

    assert response.status_code == 404
