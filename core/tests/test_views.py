from django.urls import reverse
from pytest_django.asserts import assertContains, assertRedirects


def test_homepage_requires_login(client) -> None:
    response = client.get(reverse("home"))

    assertRedirects(response, f"{reverse('login')}?next={reverse('home')}")


def test_accounts_login_redirect_preserves_next_parameter(client) -> None:
    response = client.get(f"{reverse('accounts-login')}?next={reverse('preferences')}")

    assertRedirects(response, f"{reverse('login')}?next={reverse('preferences')}")


def test_health_endpoint_returns_ok(client) -> None:
    response = client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_manifest_route_returns_pwa_metadata(client) -> None:
    response = client.get(reverse("manifest"))

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/manifest+json"
    assert response.json()["name"] == "deep-workflow"
    assert response.json()["display"] == "standalone"
    assert response.json()["start_url"] == reverse("home")
    assert any(icon["sizes"] == "192x192" for icon in response.json()["icons"])


def test_service_worker_route_returns_javascript(client) -> None:
    response = client.get(reverse("service-worker"))

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-cache"
    assert response.headers["Content-Type"] == "application/javascript"
    assertContains(response, "/static/css/app.css")
    assertContains(response, "/static/js/pwa_install.js")
