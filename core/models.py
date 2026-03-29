from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


def validate_timezone_name(value: str) -> None:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValidationError("Enter a valid timezone.") from exc


class UserPreferences(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    timezone = models.CharField(
        max_length=64,
        default=timezone.get_default_timezone_name,
        validators=[validate_timezone_name],
    )
    default_session_duration_minutes = models.PositiveSmallIntegerField(
        default=45,
        validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name_plural = "user preferences"

    def __str__(self) -> str:
        return f"Preferences for {self.user.get_username()}"

    @classmethod
    def for_user(cls, user) -> "UserPreferences":
        preferences, _ = cls.objects.get_or_create(user=user)
        return preferences
