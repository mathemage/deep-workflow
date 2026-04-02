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
    PAUSED = "paused", "Paused"
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
        preferences = UserPreferences.for_user(self.user)

        for slot, category in WorkSession.DEFAULT_STRUCTURE:
            WorkSession.objects.get_or_create(
                daily_sheet=self,
                slot=slot,
                defaults={
                    "category": category,
                    "duration_minutes": preferences.default_session_duration_minutes,
                },
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
    duration_minutes = models.PositiveSmallIntegerField(
        default=45,
        validators=[MinValueValidator(1)],
    )
    started_at = models.DateTimeField(null=True, blank=True)
    active_started_at = models.DateTimeField(null=True, blank=True)
    elapsed_seconds = models.PositiveIntegerField(default=0)
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

        errors: dict[str, list[str]] = {}

        expected_category = self.expected_category_for_slot(self.slot)
        if expected_category and self.category != expected_category:
            errors["category"] = [
                (
                    f"{self.get_slot_display()} must use the "
                    f"{expected_category} category."
                )
            ]

        if self.status == self.Status.PLANNED:
            if self.started_at is not None:
                errors.setdefault("started_at", []).append(
                    "Planned sessions cannot have a start time."
                )
            if self.active_started_at is not None:
                errors.setdefault("active_started_at", []).append(
                    "Planned sessions cannot be actively running."
                )
            if self.completed_at is not None:
                errors.setdefault("completed_at", []).append(
                    "Planned sessions cannot have a completion time."
                )
            if self.skipped_at is not None:
                errors.setdefault("skipped_at", []).append(
                    "Planned sessions cannot have a skipped time."
                )
            if self.elapsed_seconds != 0:
                errors.setdefault("elapsed_seconds", []).append(
                    "Planned sessions must reset elapsed time."
                )

        if self.status == self.Status.ACTIVE:
            if self.started_at is None:
                errors.setdefault("started_at", []).append(
                    "Active sessions must have a start time."
                )
            if self.active_started_at is None:
                errors.setdefault("active_started_at", []).append(
                    "Active sessions must track their current run."
                )
            if self.completed_at is not None:
                errors.setdefault("completed_at", []).append(
                    "Active sessions cannot have a completion time."
                )
            if self.skipped_at is not None:
                errors.setdefault("skipped_at", []).append(
                    "Active sessions cannot be skipped."
                )

        if self.status == self.Status.PAUSED:
            if self.started_at is None:
                errors.setdefault("started_at", []).append(
                    "Paused sessions must have been started."
                )
            if self.active_started_at is not None:
                errors.setdefault("active_started_at", []).append(
                    "Paused sessions cannot have an active run."
                )
            if self.completed_at is not None:
                errors.setdefault("completed_at", []).append(
                    "Paused sessions cannot have a completion time."
                )
            if self.skipped_at is not None:
                errors.setdefault("skipped_at", []).append(
                    "Paused sessions cannot be skipped."
                )

        if self.status == self.Status.COMPLETED:
            if self.started_at is None:
                errors.setdefault("started_at", []).append(
                    "Completed sessions must have a start time."
                )
            if self.active_started_at is not None:
                errors.setdefault("active_started_at", []).append(
                    "Completed sessions cannot still be running."
                )
            if self.completed_at is None:
                errors.setdefault("completed_at", []).append(
                    "Completed sessions must have a completion time."
                )
            if self.skipped_at is not None:
                errors.setdefault("skipped_at", []).append(
                    "Completed sessions cannot be skipped."
                )

        if self.status == self.Status.SKIPPED:
            if self.started_at is not None:
                errors.setdefault("started_at", []).append(
                    "Skipped sessions cannot have a start time."
                )
            if self.active_started_at is not None:
                errors.setdefault("active_started_at", []).append(
                    "Skipped sessions cannot be actively running."
                )
            if self.completed_at is not None:
                errors.setdefault("completed_at", []).append(
                    "Skipped sessions cannot have a completion time."
                )
            if self.skipped_at is None:
                errors.setdefault("skipped_at", []).append(
                    "Skipped sessions must record when they were skipped."
                )
            if self.elapsed_seconds != 0:
                errors.setdefault("elapsed_seconds", []).append(
                    "Skipped sessions must reset elapsed time."
                )

        if errors:
            raise ValidationError(errors)

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

    def can_start(self) -> bool:
        return self.status == self.Status.PLANNED

    def can_pause(self) -> bool:
        return self.status == self.Status.ACTIVE

    def can_resume(self) -> bool:
        return self.status == self.Status.PAUSED

    def can_complete(self) -> bool:
        return self.status in {self.Status.ACTIVE, self.Status.PAUSED}

    def can_skip(self) -> bool:
        return self.status == self.Status.PLANNED

    def can_mark_planned(self) -> bool:
        return self.status == self.Status.SKIPPED

    def current_elapsed_seconds(self, *, now=None) -> int:
        current_time = now or timezone.now()

        if self.status != self.Status.ACTIVE or self.active_started_at is None:
            return self.elapsed_seconds

        current_run_seconds = max(
            int((current_time - self.active_started_at).total_seconds()),
            0,
        )
        return self.elapsed_seconds + current_run_seconds

    def remaining_seconds(self, *, now=None) -> int:
        total_seconds = self.duration_minutes * 60
        return max(total_seconds - self.current_elapsed_seconds(now=now), 0)

    def ensure_no_other_active_session(self) -> None:
        if (
            WorkSession.objects.filter(
                daily_sheet__user_id=self.daily_sheet.user_id,
                status=self.Status.ACTIVE,
            )
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError(
                "Pause or complete the other active session before starting this one."
            )

    def start(self, *, now=None) -> None:
        if not self.can_start():
            raise ValidationError("Only planned sessions can be started.")

        timestamp = now or timezone.now()
        self.ensure_no_other_active_session()
        self.status = self.Status.ACTIVE
        self.started_at = timestamp
        self.active_started_at = timestamp
        self.completed_at = None
        self.skipped_at = None
        self.elapsed_seconds = 0
        self.save()

    def pause(self, *, now=None) -> None:
        if not self.can_pause():
            raise ValidationError("Only active sessions can be paused.")

        timestamp = now or timezone.now()
        self.elapsed_seconds = self.current_elapsed_seconds(now=timestamp)
        self.status = self.Status.PAUSED
        self.active_started_at = None
        self.save()

    def resume(self, *, now=None) -> None:
        if not self.can_resume():
            raise ValidationError("Only paused sessions can be resumed.")

        timestamp = now or timezone.now()
        self.ensure_no_other_active_session()
        self.status = self.Status.ACTIVE
        self.active_started_at = timestamp
        self.save()

    def complete(self, *, now=None) -> None:
        if not self.can_complete():
            raise ValidationError("Only active or paused sessions can be completed.")

        timestamp = now or timezone.now()
        self.elapsed_seconds = self.current_elapsed_seconds(now=timestamp)
        self.status = self.Status.COMPLETED
        self.active_started_at = None
        self.completed_at = timestamp
        self.save()

    def skip(self, *, now=None) -> None:
        if not self.can_skip():
            raise ValidationError("Only planned sessions can be skipped.")

        timestamp = now or timezone.now()
        self.status = self.Status.SKIPPED
        self.started_at = None
        self.active_started_at = None
        self.completed_at = None
        self.skipped_at = timestamp
        self.elapsed_seconds = 0
        self.save()

    def mark_planned(self) -> None:
        if not self.can_mark_planned():
            raise ValidationError("Only skipped sessions can be moved back to planned.")

        self.status = self.Status.PLANNED
        self.started_at = None
        self.active_started_at = None
        self.completed_at = None
        self.skipped_at = None
        self.elapsed_seconds = 0
        self.save()
