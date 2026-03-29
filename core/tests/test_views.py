from django.urls import reverse
from pytest_django.asserts import assertContains, assertTemplateUsed


def test_homepage_renders(client) -> None:
    response = client.get(reverse("home"))

    assert response.status_code == 200
    assertTemplateUsed(response, "core/home.html")
    assertContains(response, "A calm foundation for the deep-workflow app.")


def test_health_endpoint_returns_ok(client) -> None:
    response = client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
