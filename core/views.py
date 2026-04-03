from collections import Counter
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
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
    existing_slots = {session.slot for session in sessions}

    if existing_slots != set(slot for slot, _ in WorkSession.DEFAULT_STRUCTURE):
        sheet.ensure_default_work_sessions(existing_slots=existing_slots)
        sessions = list(sheet.work_sessions.order_by("slot"))

    return sheet, sessions


def format_duration_seconds(total_seconds: int) -> str:
    clamped_seconds = max(total_seconds, 0)
    minutes, seconds = divmod(clamped_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def format_accessible_remaining(total_seconds: int) -> str:
    clamped_seconds = max(total_seconds, 0)

    if clamped_seconds == 0:
        return "Time is up."

    minutes, seconds = divmod(clamped_seconds, 60)
    parts = []

    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

    return f"{' '.join(parts)} remaining."


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


def build_timer_context(session: WorkSession, *, now: datetime) -> dict[str, object]:
    remaining_seconds = session.remaining_seconds(now=now)
    return {
        "remaining_seconds": remaining_seconds,
        "remaining_display": format_duration_seconds(remaining_seconds),
        "announcement_display": format_accessible_remaining(remaining_seconds),
        "server_now_ms": int(now.timestamp() * 1000),
        "is_running": session.status == WorkSession.Status.ACTIVE,
        "summary": build_timer_summary(session),
        "actions": build_timer_actions(session),
    }


def build_session_cards(
    sessions: list[WorkSession],
    *,
    bound_form: WorkSessionUpdateForm | None = None,
    now: datetime,
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


def completion_percentage(completed_sessions: int, total_sessions: int) -> int:
    if total_sessions <= 0:
        return 0

    return round((completed_sessions / total_sessions) * 100)


def build_daily_summary(sessions: list[WorkSession]) -> dict[str, int]:
    total_sessions = len(WorkSession.DEFAULT_STRUCTURE)
    status_counts = Counter(session.status for session in sessions)
    completed_sessions = status_counts[WorkSession.Status.COMPLETED]
    active_sessions = status_counts[WorkSession.Status.ACTIVE]
    paused_sessions = status_counts[WorkSession.Status.PAUSED]
    planned_sessions = status_counts[WorkSession.Status.PLANNED]
    skipped_sessions = status_counts[WorkSession.Status.SKIPPED]

    return {
        "total_sessions": total_sessions,
        "completed_sessions": completed_sessions,
        "completion_percentage": completion_percentage(
            completed_sessions,
            total_sessions,
        ),
        "in_progress_sessions": active_sessions + paused_sessions,
        "open_sessions": active_sessions + paused_sessions + planned_sessions,
        "skipped_sessions": skipped_sessions,
    }


def completed_sessions_by_date(
    user,
    *,
    end_date: date,
    start_date: date | None = None,
) -> dict[date, int]:
    filters: dict[str, object] = {
        "user": user,
        "sheet_date__lte": end_date,
    }
    if start_date is not None:
        filters["sheet_date__gte"] = start_date

    return dict(
        DailySheet.objects.filter(**filters)
        .annotate(
            completed_sessions=Count(
                "work_sessions",
                filter=Q(work_sessions__status=WorkSession.Status.COMPLETED),
            )
        )
        .filter(completed_sessions__gt=0)
        .values_list("sheet_date", "completed_sessions")
    )


def completed_sheet_dates_desc(user, *, end_date: date):
    return (
        DailySheet.objects.filter(user=user, sheet_date__lte=end_date)
        .annotate(
            completed_sessions=Count(
                "work_sessions",
                filter=Q(work_sessions__status=WorkSession.Status.COMPLETED),
            )
        )
        .filter(completed_sessions__gt=0)
        .order_by("-sheet_date")
        .values_list("sheet_date", flat=True)
    )


def build_completion_streak(
    user,
    *,
    anchor_date: date,
    recent_completed_lookup: dict[date, int] | None = None,
    recent_start_date: date | None = None,
) -> int:
    streak_days = 0
    current_date = anchor_date

    if recent_completed_lookup is not None and recent_start_date is not None:
        while current_date >= recent_start_date:
            if recent_completed_lookup.get(current_date, 0) == 0:
                return streak_days
            streak_days += 1
            current_date -= timedelta(days=1)

    for completed_date in completed_sheet_dates_desc(
        user,
        end_date=current_date,
    ).iterator():
        if completed_date != current_date:
            break
        streak_days += 1
        current_date -= timedelta(days=1)

    return streak_days


def build_weekly_summary(user, *, anchor_date: date) -> dict[str, object]:
    week_start = anchor_date - timedelta(days=anchor_date.weekday())
    week_end = week_start + timedelta(days=6)
    completed_lookup = completed_sessions_by_date(
        user,
        start_date=week_start,
        end_date=week_end,
    )
    daily_target = len(WorkSession.DEFAULT_STRUCTURE)
    weekly_target = daily_target * 7
    week_dates = [week_start + timedelta(days=offset) for offset in range(7)]
    completed_sessions = sum(completed_lookup.values())

    return {
        "week_start": week_start,
        "week_end": week_end,
        "completed_sessions": completed_sessions,
        "total_sessions": weekly_target,
        "completion_percentage": completion_percentage(
            completed_sessions,
            weekly_target,
        ),
        "focused_days": sum(
            1 for week_date in week_dates if completed_lookup.get(week_date, 0) > 0
        ),
        "completed_days": sum(
            1
            for week_date in week_dates
            if completed_lookup.get(week_date, 0) == daily_target
        ),
        "streak_days": build_completion_streak(
            user,
            anchor_date=anchor_date,
            recent_completed_lookup=completed_lookup,
            recent_start_date=week_start,
        ),
    }


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
    daily_summary = build_daily_summary(sessions)
    weekly_summary = build_weekly_summary(user, anchor_date=sheet.sheet_date)

    return {
        "preferences": preferences,
        "sheet": sheet,
        "selected_date": sheet.sheet_date,
        "previous_date": sheet.sheet_date - timedelta(days=1),
        "next_date": sheet.sheet_date + timedelta(days=1),
        "is_today": sheet.sheet_date == today,
        "daily_summary": daily_summary,
        "weekly_summary": weekly_summary,
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

        bound_form = None

        with transaction.atomic():
            session = get_object_or_404(
                WorkSession.objects.select_for_update().select_related("daily_sheet"),
                pk=session_id,
                daily_sheet__user=request.user,
            )
            sheet_date = session.daily_sheet.sheet_date
            form = WorkSessionUpdateForm(
                request.POST,
                instance=session,
                prefix=f"session-{session.pk}",
            )

            if form.is_valid():
                session = form.save(commit=False)
                try:
                    session.save(update_fields=["goal", "notes", "updated_at"])
                except ValidationError as exc:
                    message = validation_error_message(exc)
                    form.add_error(None, message)
                    messages.error(request, message)
                    bound_form = form
                else:
                    messages.success(request, f"{session.get_slot_display()} saved.")
                    return redirect(build_session_redirect_url(session))
            else:
                bound_form = form

        context = build_home_context(
            request.user,
            preferences,
            sheet_date,
            bound_form=bound_form,
        )
        return render(request, "core/home.html", context)

    context = build_home_context(request.user, preferences, resolve_sheet_date(request))
    return render(request, "core/home.html", context)


@login_required
@require_POST
def update_session_timer(request: HttpRequest, session_id: int) -> HttpResponse:
    with transaction.atomic():
        # Lock the user row so concurrent timer updates for this user are serialized.
        request.user.__class__.objects.select_for_update().get(pk=request.user.pk)
        session = get_object_or_404(
            WorkSession.objects.select_for_update().select_related("daily_sheet"),
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
