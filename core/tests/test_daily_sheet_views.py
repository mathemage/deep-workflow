from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from pytest_django.asserts import assertContains, assertTemplateUsed

from core.models import DailySheet, UserPreferences, WorkSession


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        username="jules",
        password="calm-focus-123",
    )


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


def test_home_strips_whitespace_from_selected_day(client, user) -> None:
    client.force_login(user)

    response = client.get(reverse("home"), {"date": "2026-04-05 "})

    assert response.status_code == 200
    assert response.context["selected_date"] == date(2026, 4, 5)


def test_home_rejects_invalid_selected_day(client, user) -> None:
    client.force_login(user)

    response = client.get(reverse("home"), {"date": "not-a-date"})

    assert response.status_code == 404


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
            f"session-{session.pk}-status": WorkSession.Status.ACTIVE,
        },
        follow=True,
    )

    assert response.status_code == 200
    assertContains(response, "Personal 2 saved.")

    session.refresh_from_db()
    assert session.goal == "Ship the card layout"
    assert session.notes == "Keep the copy calm and focused."
    assert session.status == WorkSession.Status.ACTIVE


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
            f"session-{session.pk}-status": WorkSession.Status.PLANNED,
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
            f"session-{other_session.pk}-status": WorkSession.Status.COMPLETED,
        },
    )

    assert response.status_code == 404
