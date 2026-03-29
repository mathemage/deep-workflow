from django.conf import settings
from django.utils import timezone

from .models import UserPreferences


class UserTimezoneMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            timezone_name = settings.TIME_ZONE
            try:
                timezone_name = request.user.preferences.timezone
            except UserPreferences.DoesNotExist:
                pass

            timezone.activate(timezone_name)
        else:
            timezone.deactivate()

        return self.get_response(request)
