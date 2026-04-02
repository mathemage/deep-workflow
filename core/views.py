from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import UserPreferencesForm, WorkSessionUpdateForm
from .models import DailySheet, UserPreferences, WorkSession

SESSION_TIMER_ACTIONS = {
    "start": {"label": "Start timer", "button_class": "button"},
    "pause": {"label": "Pause timer", "button_class": "button button-secondary"},
    "resume": {"label": "Resume timer", "button_class": "button"},
    "complete": {"label": "Complete session", "button_class": "button"},
    "skip": {"label": "Mark skipped", "button_class": "button button-secondary"},
    "mark_planned": {
        "label": "Move back to planned",
        "button_class": "button button-secondary",
    },
}
SESSION_TIMER_SUCCESS_MESSAGES = {
    "start": "started.",
    "pause": "paused.",
    "resume": "resumed.",
    "complete": "completed.",
    "skip": "marked skipped.",
    "mark_planned": "moved back to planned.",
}


class DeepWorkflowLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True


def resolve_sheet_date(request: HttpRequest) -> date:
    raw_date = request.GET.get("date")

    if not raw_date:
        return timezone.localdate()

    normalized_date = raw_date.strip()

    try:
        return date.fromisoformat(normalized_date)
    except ValueError as exc:
        raise Http404("Invalid daily sheet date.") from exc


def get_daily_sheet(user, sheet_date: date) -> tuple[DailySheet, list[WorkSession]]:
    sheet, _ = DailySheet.objects.get_or_create(user=user, sheet_date=sheet_date)
    sessions = list(sheet.work_sessions.order_by("slot"))
    return sheet, sessions


def format_duration_seconds(total_seconds: int) -> str:
    clamped_seconds = max(total_seconds, 0)
    minutes, seconds = divmod(clamped_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def build_timer_actions(session: WorkSession) -> list[dict[str, str]]:
    if session.can_start():
        action_keys = ("start", "skip")
    elif session.can_pause():
        action_keys = ("pause", "complete")
    elif session.can_resume():
        action_keys = ("resume", "complete")
    elif session.can_mark_planned():
        action_keys = ("mark_planned",)
    else:
        action_keys = ()

    return [
        {"value": action_key, **SESSION_TIMER_ACTIONS[action_key]}
        for action_key in action_keys
    ]


def build_timer_summary(session: WorkSession) -> str:
    duration_display = format_duration_seconds(session.duration_minutes * 60)

    if session.status == WorkSession.Status.ACTIVE:
        return "Running from the server-backed timer state."
    if session.status == WorkSession.Status.PAUSED:
        return "Paused. Resume when you're ready to continue."
    if session.status == WorkSession.Status.COMPLETED:
        return "Completed for today."
    if session.status == WorkSession.Status.SKIPPED:
        return "Skipped for this day."
    return f"{duration_display} ready when you start."


def build_timer_context(session: WorkSession, *, now) -> dict[str, object]:
    remaining_seconds = session.remaining_seconds(now=now)
    return {
        "remaining_seconds": remaining_seconds,
        "remaining_display": format_duration_seconds(remaining_seconds),
        "is_running": session.status == WorkSession.Status.ACTIVE,
        "summary": build_timer_summary(session),
        "actions": build_timer_actions(session),
    }


def build_session_cards(
    sessions: list[WorkSession],
    *,
    bound_form: WorkSessionUpdateForm | None = None,
    now,
) -> list[dict[str, object]]:
    session_cards = []

    for session in sessions:
        prefix = f"session-{session.pk}"
        form = (
            bound_form
            if bound_form is not None and bound_form.instance.pk == session.pk
            else WorkSessionUpdateForm(instance=session, prefix=prefix)
        )
        session_cards.append(
            {
                "session": session,
                "form": form,
                "timer": build_timer_context(session, now=now),
            }
        )

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
    now = timezone.now()

    return {
        "preferences": preferences,
        "sheet": sheet,
        "selected_date": sheet.sheet_date,
        "previous_date": sheet.sheet_date - timedelta(days=1),
        "next_date": sheet.sheet_date + timedelta(days=1),
        "is_today": sheet.sheet_date == today,
        "session_cards": build_session_cards(
            sessions,
            bound_form=bound_form,
            now=now,
        ),
    }


def build_session_redirect_url(session: WorkSession) -> str:
    return (
        f"{reverse('home')}?date={session.daily_sheet.sheet_date.isoformat()}"
        f"#session-{session.slot}"
    )


def validation_error_message(exc: ValidationError) -> str:
    if hasattr(exc, "message_dict"):
        return "; ".join(
            message
            for messages_for_field in exc.message_dict.values()
            for message in messages_for_field
        )
    return "; ".join(exc.messages)


def perform_timer_action(session: WorkSession, action: str, *, now) -> str:
    if action == "start":
        session.start(now=now)
    elif action == "pause":
        session.pause(now=now)
    elif action == "resume":
        session.resume(now=now)
    elif action == "complete":
        session.complete(now=now)
    elif action == "skip":
        session.skip(now=now)
    elif action == "mark_planned":
        session.mark_planned()
    else:
        raise Http404("Session action not found.")

    return SESSION_TIMER_SUCCESS_MESSAGES[action]


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
            return redirect(build_session_redirect_url(session))

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
@require_POST
def update_session_timer(request: HttpRequest, session_id: int) -> HttpResponse:
    with transaction.atomic():
        list(
            DailySheet.objects.select_for_update()
            .filter(user=request.user)
            .values_list("pk", flat=True)
        )
        session = get_object_or_404(
            WorkSession.objects.select_related("daily_sheet"),
            pk=session_id,
            daily_sheet__user=request.user,
        )

        try:
            success_message = perform_timer_action(
                session,
                request.POST.get("action", ""),
                now=timezone.now(),
            )
        except ValidationError as exc:
            messages.error(request, validation_error_message(exc))
        else:
            messages.success(request, f"{session.get_slot_display()} {success_message}")

    return redirect(build_session_redirect_url(session))


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
