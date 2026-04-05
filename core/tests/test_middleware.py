import uuid
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory
from django.utils import timezone

from core.logging import get_request_id
from core.middleware import RequestIDMiddleware, UserTimezoneMiddleware
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


def test_request_id_middleware_uses_incoming_request_id_header() -> None:
    request = RequestFactory().get("/", HTTP_X_REQUEST_ID=" trace-123 ")

    def get_response(request):
        assert request.request_id == "trace-123"
        assert get_request_id() == "trace-123"
        return HttpResponse("ok")

    middleware = RequestIDMiddleware(get_response)

    response = middleware(request)

    assert response.status_code == 200
    assert response["X-Request-ID"] == "trace-123"
    assert get_request_id() == "-"


def test_request_id_middleware_rejects_invalid_header_characters() -> None:
    request = RequestFactory().get("/")
    request.META["HTTP_X_REQUEST_ID"] = "trace-123\r\nx-bad: injected"

    def get_response(request):
        assert request.request_id == "12345678123456781234567812345678"
        assert get_request_id() == "12345678123456781234567812345678"
        return HttpResponse("ok")

    middleware = RequestIDMiddleware(get_response)

    with patch(
        "core.middleware.uuid.uuid4",
        return_value=uuid.UUID("12345678-1234-5678-1234-567812345678"),
    ):
        response = middleware(request)

    assert response.status_code == 200
    assert response["X-Request-ID"] == "12345678123456781234567812345678"
    assert get_request_id() == "-"


def test_request_id_middleware_rejects_overly_long_header_values() -> None:
    request = RequestFactory().get("/", HTTP_X_REQUEST_ID="x" * 129)

    def get_response(request):
        assert request.request_id == "12345678123456781234567812345678"
        return HttpResponse("ok")

    middleware = RequestIDMiddleware(get_response)

    with patch(
        "core.middleware.uuid.uuid4",
        return_value=uuid.UUID("12345678-1234-5678-1234-567812345678"),
    ):
        response = middleware(request)

    assert response.status_code == 200
    assert response["X-Request-ID"] == "12345678123456781234567812345678"


def test_request_id_middleware_generates_and_resets_request_id_on_exception() -> None:
    request = RequestFactory().get("/")

    def get_response(request):
        assert request.request_id == "12345678123456781234567812345678"
        assert get_request_id() == "12345678123456781234567812345678"
        raise RuntimeError("boom")

    middleware = RequestIDMiddleware(get_response)

    with patch(
        "core.middleware.uuid.uuid4",
        return_value=uuid.UUID("12345678-1234-5678-1234-567812345678"),
    ):
        with pytest.raises(RuntimeError, match="boom"):
            middleware(request)

    assert get_request_id() == "-"
