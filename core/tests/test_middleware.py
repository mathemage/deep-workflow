import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory
from django.utils import timezone

from core.middleware import UserTimezoneMiddleware
from core.models import UserPreferences


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        username="casey",
        password="calm-focus-123",
    )


def test_user_timezone_middleware_restores_previous_timezone_after_response(
    user,
) -> None:
    UserPreferences.objects.create(user=user, timezone="America/New_York")
    request = RequestFactory().get("/")
    request.user = user

    def get_response(request):
        assert timezone.get_current_timezone_name() == "America/New_York"
        return HttpResponse("ok")

    middleware = UserTimezoneMiddleware(get_response)

    timezone.deactivate()

    response = middleware(request)

    assert response.status_code == 200
    assert timezone.get_current_timezone_name() == settings.TIME_ZONE


def test_user_timezone_middleware_restores_previous_timezone_after_exception(
    user,
) -> None:
    UserPreferences.objects.create(user=user, timezone="America/New_York")
    request = RequestFactory().get("/")
    request.user = user

    def get_response(request):
        assert timezone.get_current_timezone_name() == "America/New_York"
        raise RuntimeError("boom")

    middleware = UserTimezoneMiddleware(get_response)

    timezone.deactivate()

    with pytest.raises(RuntimeError, match="boom"):
        middleware(request)

    assert timezone.get_current_timezone_name() == settings.TIME_ZONE
