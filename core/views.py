from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import UserPreferencesForm, WorkSessionUpdateForm
from .models import DailySheet, UserPreferences, WorkSession


class DeepWorkflowLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True


def resolve_sheet_date(request: HttpRequest) -> date:
    raw_date = request.GET.get("date")

    if not raw_date:
        return timezone.localdate()

    try:
        return date.fromisoformat(raw_date)
    except ValueError as exc:
        raise Http404("Invalid daily sheet date.") from exc


def get_daily_sheet(user, sheet_date: date) -> tuple[DailySheet, list[WorkSession]]:
    sheet, _ = DailySheet.objects.get_or_create(user=user, sheet_date=sheet_date)
    sessions = list(sheet.work_sessions.order_by("slot"))
    return sheet, sessions


def build_session_cards(
    sessions: list[WorkSession],
    *,
    bound_form: WorkSessionUpdateForm | None = None,
) -> list[dict[str, object]]:
    session_cards = []

    for session in sessions:
        prefix = f"session-{session.pk}"
        form = (
            bound_form
            if bound_form is not None and bound_form.instance.pk == session.pk
            else WorkSessionUpdateForm(instance=session, prefix=prefix)
        )
        session_cards.append({"session": session, "form": form})

    return session_cards


def build_home_context(
    user,
    preferences: UserPreferences,
    sheet_date: date,
    *,
    bound_form: WorkSessionUpdateForm | None = None,
) -> dict[str, object]:
    sheet, sessions = get_daily_sheet(user, sheet_date)
    today = timezone.localdate()

    return {
        "preferences": preferences,
        "sheet": sheet,
        "selected_date": sheet.sheet_date,
        "previous_date": sheet.sheet_date - timedelta(days=1),
        "next_date": sheet.sheet_date + timedelta(days=1),
        "is_today": sheet.sheet_date == today,
        "session_cards": build_session_cards(sessions, bound_form=bound_form),
    }


@login_required
def home(request: HttpRequest) -> HttpResponse:
    preferences = UserPreferences.for_user(request.user)

    if request.method == "POST":
        try:
            session_id = int(request.POST["session_id"])
        except (KeyError, ValueError) as exc:
            raise Http404("Session not found.") from exc

        session = get_object_or_404(
            WorkSession.objects.select_related("daily_sheet"),
            pk=session_id,
            daily_sheet__user=request.user,
        )
        form = WorkSessionUpdateForm(
            request.POST,
            instance=session,
            prefix=f"session-{session.pk}",
        )

        if form.is_valid():
            form.save()
            messages.success(request, f"{session.get_slot_display()} saved.")
            return redirect(
                f"{reverse('home')}?date={session.daily_sheet.sheet_date.isoformat()}"
                f"#session-{session.slot}"
            )

        context = build_home_context(
            request.user,
            preferences,
            session.daily_sheet.sheet_date,
            bound_form=form,
        )
        return render(request, "core/home.html", context)

    context = build_home_context(request.user, preferences, resolve_sheet_date(request))
    return render(request, "core/home.html", context)


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
