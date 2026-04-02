from zoneinfo import available_timezones

from django import forms

from .models import UserPreferences, WorkSession, validate_timezone_name

TIMEZONE_OPTIONS = tuple(sorted(available_timezones()))


class UserPreferencesForm(forms.ModelForm):
    timezone = forms.CharField(
        help_text="Used for daily sheet dates and future session scheduling.",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "list": "timezone-options",
                "spellcheck": "false",
            }
        ),
    )

    class Meta:
        model = UserPreferences
        fields = ("timezone", "default_session_duration_minutes")
        labels = {
            "default_session_duration_minutes": "Default session duration",
        }
        help_texts = {
            "default_session_duration_minutes": "Minutes for new sessions.",
        }
        widgets = {
            "default_session_duration_minutes": forms.NumberInput(
                attrs={"min": "1", "step": "5"}
            ),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.timezone_options = TIMEZONE_OPTIONS

    def clean_timezone(self) -> str:
        value = self.cleaned_data["timezone"].strip()
        validate_timezone_name(value)
        return value


class WorkSessionUpdateForm(forms.ModelForm):
    class Meta:
        model = WorkSession
        fields = ("goal", "notes", "status")
        help_texts = {
            "goal": "Keep it concrete and finishable.",
            "notes": "Optional context, blockers, or follow-up notes.",
            "status": (
                "Reflect whether the session is planned, active, completed, or skipped."
            ),
        }
        widgets = {
            "goal": forms.TextInput(
                attrs={"placeholder": "What would make this session feel complete?"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "placeholder": "Capture context, reminders, or next steps.",
                    "rows": 4,
                }
            ),
        }
