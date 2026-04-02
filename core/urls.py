from django.contrib.auth.views import LogoutView
from django.urls import path
from django.views.generic import RedirectView

from .views import (
    DeepWorkflowLoginView,
    health,
    home,
    preferences,
    update_session_timer,
)

urlpatterns = [
    path("login/", DeepWorkflowLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("settings/", preferences, name="preferences"),
    path(
        "sessions/<int:session_id>/timer/",
        update_session_timer,
        name="session-timer",
    ),
    path("", home, name="home"),
    path("health/", health, name="health"),
    path(
        "accounts/login/",
        RedirectView.as_view(pattern_name="login", permanent=False, query_string=True),
        name="accounts-login",
    ),
]
