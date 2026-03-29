from django.contrib import admin

from .models import UserPreferences


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ("user", "timezone", "default_session_duration_minutes")
    search_fields = ("user__username", "user__email", "timezone")
