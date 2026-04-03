from django.contrib import admin
from django.db.models import Count

from .models import DailySheet, UserPreferences, WorkSession


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ("user", "timezone", "default_session_duration_minutes")
    search_fields = ("user__username", "user__email", "timezone")


class WorkSessionInline(admin.TabularInline):
    model = WorkSession
    extra = 0
    max_num = 4
    can_delete = False
    fields = (
        "slot",
        "category",
        "status",
        "goal",
        "notes",
        "duration_minutes",
        "started_at",
        "active_started_at",
        "elapsed_seconds",
        "completed_at",
        "skipped_at",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("slot", "category", "created_at", "updated_at")
    ordering = ("slot",)
    show_change_link = True

    def has_add_permission(self, request, obj=None) -> bool:
        return False


@admin.register(DailySheet)
class DailySheetAdmin(admin.ModelAdmin):
    list_display = ("user", "sheet_date", "session_count", "created_at", "updated_at")
    search_fields = ("user__username", "user__email")
    date_hierarchy = "sheet_date"
    list_select_related = ("user",)
    ordering = ("-sheet_date", "user__username")
    inlines = [WorkSessionInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(work_session_count=Count("work_sessions"))

    @admin.display(description="Sessions", ordering="work_session_count")
    def session_count(self, obj: DailySheet) -> int:
        return getattr(obj, "work_session_count", obj.work_sessions.count())


@admin.register(WorkSession)
class WorkSessionAdmin(admin.ModelAdmin):
    list_display = (
        "daily_sheet",
        "slot",
        "category",
        "status",
        "duration_minutes",
        "started_at",
        "active_started_at",
        "elapsed_seconds",
        "completed_at",
        "skipped_at",
    )
    list_filter = ("category", "status", "slot")
    search_fields = (
        "daily_sheet__user__username",
        "daily_sheet__user__email",
        "goal",
        "notes",
    )
    list_select_related = ("daily_sheet", "daily_sheet__user")
    ordering = ("-daily_sheet__sheet_date", "slot")
    readonly_fields = ("daily_sheet", "slot", "category", "created_at", "updated_at")
    fields = (
        "daily_sheet",
        "slot",
        "category",
        "status",
        "goal",
        "notes",
        "duration_minutes",
        "started_at",
        "active_started_at",
        "elapsed_seconds",
        "completed_at",
        "skipped_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
