import uuid

from django.conf import settings
from django.utils import timezone

from .logging import reset_request_id, set_request_id
from .models import UserPreferences


class RequestIDMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request):
        request_id = (
            request.META.get("HTTP_X_REQUEST_ID", "").strip() or uuid.uuid4().hex
        )
        request.request_id = request_id
        request_id_token = set_request_id(request_id)

        try:
            response = self.get_response(request)
        finally:
            reset_request_id(request_id_token)

        response["X-Request-ID"] = request_id
        return response


class UserTimezoneMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request):
        timezone_name = None

        if request.user.is_authenticated:
            timezone_name = settings.TIME_ZONE
            try:
                timezone_name = request.user.preferences.timezone
            except UserPreferences.DoesNotExist:
                pass

        with timezone.override(timezone_name):
            return self.get_response(request)
