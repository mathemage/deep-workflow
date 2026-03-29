from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from .forms import UserPreferencesForm
from .models import UserPreferences


class DeepWorkflowLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True


@login_required
def home(request: HttpRequest) -> HttpResponse:
    preferences = UserPreferences.for_user(request.user)
    return render(request, "core/home.html", {"preferences": preferences})


@login_required
def preferences(request: HttpRequest) -> HttpResponse:
    user_preferences = UserPreferences.for_user(request.user)

    if request.method == "POST":
        form = UserPreferencesForm(request.POST, instance=user_preferences)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings saved.")
            return redirect("preferences")
    else:
        form = UserPreferencesForm(instance=user_preferences)

    return render(
        request,
        "core/preferences.html",
        {
            "form": form,
            "timezone_options": form.timezone_options,
        },
    )


def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})
