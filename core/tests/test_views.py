from django.urls import reverse
from pytest_django.asserts import assertRedirects


def test_homepage_requires_login(client) -> None:
    response = client.get(reverse("home"))

    assertRedirects(response, f"{reverse('login')}?next={reverse('home')}")


def test_health_endpoint_returns_ok(client) -> None:
    response = client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
