from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import IntegrityError, models, transaction
from django.db.models import Q
from django.utils import timezone


def validate_timezone_name(value: str) -> None:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValidationError("Enter a valid timezone.") from exc


class WorkSessionCategory(models.TextChoices):
    PERSONAL = "personal", "Personal"
    ADMIN = "admin", "Admin"


class WorkSessionStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    SKIPPED = "skipped", "Skipped"


class WorkSessionSlot(models.IntegerChoices):
    PERSONAL_1 = 1, "Personal 1"
    PERSONAL_2 = 2, "Personal 2"
    PERSONAL_3 = 3, "Personal 3"
    ADMIN = 4, "Admin"


WORK_SESSION_DEFAULT_STRUCTURE = (
    (WorkSessionSlot.PERSONAL_1, WorkSessionCategory.PERSONAL),
    (WorkSessionSlot.PERSONAL_2, WorkSessionCategory.PERSONAL),
    (WorkSessionSlot.PERSONAL_3, WorkSessionCategory.PERSONAL),
    (WorkSessionSlot.ADMIN, WorkSessionCategory.ADMIN),
)
WORK_SESSION_PERSONAL_SLOTS = tuple(
    slot
    for slot, category in WORK_SESSION_DEFAULT_STRUCTURE
    if category == WorkSessionCategory.PERSONAL
)
WORK_SESSION_CATEGORY_BY_SLOT = dict(WORK_SESSION_DEFAULT_STRUCTURE)


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
        try:
            preferences, _ = cls.objects.get_or_create(user=user)
        except IntegrityError:
            preferences = cls.objects.get(user=user)
        return preferences


class DailySheet(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_sheets",
    )
    sheet_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-sheet_date", "user_id")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "sheet_date"),
                name="daily_sheet_unique_user_date",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user.get_username()} - {self.sheet_date.isoformat()}"

    def save(self, *args, **kwargs) -> None:
        with transaction.atomic():
            super().save(*args, **kwargs)
            self.ensure_default_work_sessions()

    def ensure_default_work_sessions(self) -> None:
        for slot, category in WorkSession.DEFAULT_STRUCTURE:
            WorkSession.objects.get_or_create(
                daily_sheet=self,
                slot=slot,
                defaults={"category": category},
            )


class WorkSessionQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError(
            "Work sessions are fixed for each daily sheet and cannot be "
            "deleted individually."
        )


class WorkSession(models.Model):
    Category = WorkSessionCategory
    Status = WorkSessionStatus
    Slot = WorkSessionSlot
    DEFAULT_STRUCTURE = WORK_SESSION_DEFAULT_STRUCTURE

    objects = WorkSessionQuerySet.as_manager()

    daily_sheet = models.ForeignKey(
        DailySheet,
        on_delete=models.CASCADE,
        related_name="work_sessions",
    )
    slot = models.PositiveSmallIntegerField(choices=Slot.choices)
    category = models.CharField(max_length=16, choices=Category.choices)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    goal = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    skipped_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("daily_sheet_id", "slot")
        constraints = [
            models.UniqueConstraint(
                fields=("daily_sheet", "slot"),
                name="work_session_unique_sheet_slot",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        slot__in=WORK_SESSION_PERSONAL_SLOTS,
                        category=WorkSessionCategory.PERSONAL,
                    )
                    | Q(
                        slot=WorkSessionSlot.ADMIN,
                        category=WorkSessionCategory.ADMIN,
                    )
                ),
                name="work_session_slot_category_match",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.daily_sheet} - {self.get_slot_display()}"

    def clean(self) -> None:
        super().clean()

        expected_category = self.expected_category_for_slot(self.slot)
        if expected_category and self.category != expected_category:
            raise ValidationError(
                {
                    "category": (
                        f"{self.get_slot_display()} must use the "
                        f"{expected_category} category."
                    )
                }
            )

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Work sessions are fixed for each daily sheet and cannot be "
            "deleted individually."
        )

    @classmethod
    def expected_category_for_slot(cls, slot: int | None) -> str | None:
        return WORK_SESSION_CATEGORY_BY_SLOT.get(slot)
