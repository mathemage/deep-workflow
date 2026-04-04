import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from pytest_django.asserts import (
    assertContains,
    assertRedirects,
    assertTemplateUsed,
)

from core.models import UserPreferences


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        username="alex",
        password="calm-focus-123",
    )


def test_login_page_renders(client) -> None:
    response = client.get(reverse("login"))

    assert response.status_code == 200
    assertTemplateUsed(response, "registration/login.html")
    assertContains(response, "Log in")
    assertContains(response, 'rel="manifest"')


def test_login_redirects_to_dashboard_and_creates_default_preferences(
    client,
    user,
) -> None:
    response = client.post(
        reverse("login"),
        {
            "username": user.username,
            "password": "calm-focus-123",
        },
        follow=True,
    )

    assert response.status_code == 200
    assertTemplateUsed(response, "core/home.html")

    preferences = UserPreferences.objects.get(user=user)
    assert preferences.timezone == settings.TIME_ZONE
    assert preferences.default_session_duration_minutes == 45


def test_login_respects_next_parameter(client, user) -> None:
    response = client.post(
        reverse("login"),
        {
            "username": user.username,
            "password": "calm-focus-123",
            "next": reverse("preferences"),
        },
    )

    assertRedirects(response, reverse("preferences"))


def test_login_accepts_csrf_protected_post(user) -> None:
    client = Client(enforce_csrf_checks=True)

    response = client.get(reverse("login"))

    assert response.status_code == 200
    csrf_token = client.cookies["csrftoken"].value

    response = client.post(
        reverse("login"),
        {
            "username": user.username,
            "password": "calm-focus-123",
        },
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assertRedirects(response, reverse("home"))


def test_logout_redirects_to_login(client, user) -> None:
    client.force_login(user)

    response = client.post(reverse("logout"))

    assertRedirects(response, reverse("login"))

    follow_up = client.get(reverse("home"))
    assertRedirects(follow_up, f"{reverse('login')}?next={reverse('home')}")


def test_preferences_page_updates_values(client, user) -> None:
    client.force_login(user)

    response = client.post(
        reverse("preferences"),
        {
            "timezone": "America/New_York",
            "default_session_duration_minutes": "60",
        },
        follow=True,
    )

    assertRedirects(response, reverse("preferences"))
    assertContains(response, "Settings saved.")

    preferences = UserPreferences.objects.get(user=user)
    assert preferences.timezone == "America/New_York"
    assert preferences.default_session_duration_minutes == 60


def test_preferences_page_rejects_invalid_timezone(client, user) -> None:
    client.force_login(user)

    response = client.post(
        reverse("preferences"),
        {
            "timezone": "Mars/Olympus_Mons",
            "default_session_duration_minutes": "45",
        },
    )

    assert response.status_code == 200
    assertContains(response, "Enter a valid timezone.")
