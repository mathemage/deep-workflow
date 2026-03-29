from zoneinfo import available_timezones

from django import forms

from .models import UserPreferences, validate_timezone_name

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
