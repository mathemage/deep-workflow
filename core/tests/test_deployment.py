import json
import os
import subprocess
import sys

from django.conf import settings

from deep_workflow.deployment import (
    HSTS_PRELOAD_MIN_SECONDS,
    build_allowed_hosts,
    build_csrf_trusted_origins,
    canonical_deployment_url,
    default_debug,
    deployment_environment,
    hosted_environment,
    hsts_preload_enabled,
)

IMPORT_HOSTED_SETTINGS_COMMAND = (
    "import environ; "
    "environ.Env.read_env = staticmethod(lambda *args, **kwargs: None); "
    "import deep_workflow.settings as settings; "
    "from django.conf import settings as django_settings; "
    "print(json.dumps(["
    "settings.HOSTED_SQLITE_FALLBACK, "
    "django_settings.SESSION_ENGINE, "
    "django_settings.MESSAGE_STORAGE"
    "]))"
)
IMPORT_HOSTED_SETTINGS_SNIPPET = (
    "import environ; "
    "environ.Env.read_env = staticmethod(lambda *args, **kwargs: None); "
    "import deep_workflow.settings"
)


def test_build_allowed_hosts_adds_vercel_runtime_hosts() -> None:
    environ = {
        "APP_BASE_URL": "https://deep-workflow.vercel.app",
        "VERCEL_BRANCH_URL": "deep-workflow-git-production-deploy-mathemage.vercel.app",
        "VERCEL_URL": "deep-workflow-9vxtqhmvi-mathemage.vercel.app",
    }

    assert build_allowed_hosts(["localhost", "127.0.0.1", "testserver"], environ) == [
        "localhost",
        "127.0.0.1",
        "testserver",
        "deep-workflow.vercel.app",
        "deep-workflow-git-production-deploy-mathemage.vercel.app",
        "deep-workflow-9vxtqhmvi-mathemage.vercel.app",
    ]


def test_build_csrf_trusted_origins_adds_https_runtime_origins() -> None:
    environ = {
        "APP_BASE_URL": "https://deep-workflow.vercel.app",
        "VERCEL_URL": "deep-workflow-9vxtqhmvi-mathemage.vercel.app",
    }

    assert build_csrf_trusted_origins(
        ["http://localhost:8000", "http://127.0.0.1:8000"],
        environ,
    ) == [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://deep-workflow.vercel.app",
        "https://deep-workflow-9vxtqhmvi-mathemage.vercel.app",
    ]


def test_deployment_environment_helpers_detect_hosted_runtime() -> None:
    environ = {
        "VERCEL_ENV": "preview",
        "VERCEL_PROJECT_PRODUCTION_URL": "deep-workflow.vercel.app",
    }

    assert deployment_environment(environ) == "preview"
    assert hosted_environment(environ) is True
    assert canonical_deployment_url(environ) == "https://deep-workflow.vercel.app"


def test_canonical_deployment_url_prefers_preview_url_for_preview_env() -> None:
    environ = {
        "APP_BASE_URL": "https://deep-workflow.vercel.app",
        "VERCEL_BRANCH_URL": "deep-workflow-git-production-deploy-mathemage.vercel.app",
        "VERCEL_ENV": "preview",
    }

    assert (
        canonical_deployment_url(environ)
        == "https://deep-workflow-git-production-deploy-mathemage.vercel.app"
    )


def test_default_debug_uses_loaded_vercel_flags() -> None:
    assert default_debug({}) is True
    assert default_debug({"VERCEL_ENV": "production"}) is False
    assert default_debug({"VERCEL": "true"}) is False


def test_hsts_preload_enabled_requires_explicit_safe_opt_in() -> None:
    assert (
        hsts_preload_enabled(
            preload_opt_in=False,
            secure_hsts_seconds=HSTS_PRELOAD_MIN_SECONDS,
            include_subdomains=True,
        )
        is False
    )
    assert (
        hsts_preload_enabled(
            preload_opt_in=True,
            secure_hsts_seconds=HSTS_PRELOAD_MIN_SECONDS - 1,
            include_subdomains=True,
        )
        is False
    )
    assert (
        hsts_preload_enabled(
            preload_opt_in=True,
            secure_hsts_seconds=HSTS_PRELOAD_MIN_SECONDS,
            include_subdomains=False,
        )
        is False
    )
    assert (
        hsts_preload_enabled(
            preload_opt_in=True,
            secure_hsts_seconds=HSTS_PRELOAD_MIN_SECONDS,
            include_subdomains=True,
        )
        is True
    )


def test_request_id_middleware_precedes_whitenoise() -> None:
    assert settings.MIDDLEWARE.index(
        "core.middleware.RequestIDMiddleware"
    ) < settings.MIDDLEWARE.index(
        "whitenoise.middleware.WhiteNoiseMiddleware",
    )


def load_hosted_settings(
    *,
    enable_fallback: bool | None,
    database_url: str | None = "sqlite:///db.sqlite3",
) -> tuple[bool, str, str]:
    env = os.environ.copy()
    env.update(
        {
            "DJANGO_DEBUG": "False",
            "DJANGO_SETTINGS_MODULE": "deep_workflow.settings",
            "DJANGO_SECRET_KEY": "x" * 64,
            "VERCEL_ENV": "production",
            "VERCEL": "1",
        }
    )
    if database_url is None:
        env.pop("DATABASE_URL", None)
    else:
        env["DATABASE_URL"] = database_url
    if enable_fallback is None:
        env.pop("DJANGO_ENABLE_HOSTED_SQLITE_FALLBACK", None)
    else:
        env["DJANGO_ENABLE_HOSTED_SQLITE_FALLBACK"] = "1" if enable_fallback else "0"
    command = [
        sys.executable,
        "-c",
        f"import json; {IMPORT_HOSTED_SETTINGS_COMMAND}",
    ]
    result = subprocess.run(
        command,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(json.loads(result.stdout))


def run_hosted_settings_import(
    *,
    database_url: str | None,
    enable_fallback: bool | None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "DJANGO_DEBUG": "False",
            "DJANGO_SECRET_KEY": "x" * 64,
            "VERCEL_ENV": "production",
            "VERCEL": "1",
        }
    )
    if database_url is None:
        env.pop("DATABASE_URL", None)
    else:
        env["DATABASE_URL"] = database_url
    if enable_fallback is None:
        env.pop("DJANGO_ENABLE_HOSTED_SQLITE_FALLBACK", None)
    else:
        env["DJANGO_ENABLE_HOSTED_SQLITE_FALLBACK"] = "1" if enable_fallback else "0"
    return subprocess.run(
        [sys.executable, "-c", IMPORT_HOSTED_SETTINGS_SNIPPET],
        env=env,
        capture_output=True,
        text=True,
    )


def test_hosted_sqlite_fallback_is_disabled_by_default_when_flag_is_zero() -> None:
    result = run_hosted_settings_import(
        database_url="sqlite:///db.sqlite3",
        enable_fallback=False,
    )
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert "Hosted deployments require one of these database configurations" in (
        result.stderr
    )
    assert "DJANGO_ENABLE_HOSTED_SQLITE_FALLBACK=1" in result.stderr


def test_hosted_sqlite_fallback_is_disabled_by_default_when_flag_is_unset() -> None:
    result = run_hosted_settings_import(
        database_url="sqlite:///db.sqlite3",
        enable_fallback=None,
    )
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert "Hosted deployments require one of these database configurations" in (
        result.stderr
    )
    assert "DJANGO_ENABLE_HOSTED_SQLITE_FALLBACK=1" in result.stderr


def test_hosted_sqlite_fallback_is_disabled_when_database_url_is_unset() -> None:
    result = run_hosted_settings_import(
        database_url=None,
        enable_fallback=None,
    )
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert "Hosted deployments require one of these database configurations" in (
        result.stderr
    )
    assert "DJANGO_ENABLE_HOSTED_SQLITE_FALLBACK=1" in result.stderr


def test_hosted_sqlite_fallback_requires_explicit_opt_in() -> None:
    hosted_settings = load_hosted_settings(enable_fallback=True)
    hosted_sqlite_fallback, session_engine, message_storage = hosted_settings

    assert hosted_sqlite_fallback is True
    assert session_engine == "django.contrib.sessions.backends.signed_cookies"
    assert message_storage == "django.contrib.messages.storage.cookie.CookieStorage"


def test_hosted_sqlite_fallback_requires_explicit_database_url() -> None:
    result = run_hosted_settings_import(
        database_url=None,
        enable_fallback=True,
    )
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert "Hosted deployments require one of these database configurations" in (
        result.stderr
    )
    assert "DJANGO_ENABLE_HOSTED_SQLITE_FALLBACK=1" in result.stderr


def test_hosted_sqlite_fallback_flag_ignored_for_postgresql() -> None:
    hosted_sqlite_fallback, session_engine, message_storage = load_hosted_settings(
        enable_fallback=True,
        database_url="postgresql://testuser:testpass@localhost:5432/testdb",
    )

    assert hosted_sqlite_fallback is False
    assert session_engine != "django.contrib.sessions.backends.signed_cookies"
    assert message_storage != "django.contrib.messages.storage.cookie.CookieStorage"


def test_hosted_sqlite_fallback_is_not_applied_to_invalid_database_url() -> None:
    env = os.environ.copy()
    env.update(
        {
            "DJANGO_DEBUG": "False",
            "DJANGO_SECRET_KEY": "x" * 64,
            "VERCEL_ENV": "production",
            "VERCEL": "1",
            "DATABASE_URL": "invalid://definitely-not-a-supported-database-url",
            "DJANGO_ENABLE_HOSTED_SQLITE_FALLBACK": "1",
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import environ; "
                "environ.Env.read_env = staticmethod(lambda *args, **kwargs: None); "
                "import deep_workflow.settings"
            ),
        ],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert "Hosted deployments require one of these database configurations" in (
        result.stderr
    )
    assert "DJANGO_ENABLE_HOSTED_SQLITE_FALLBACK=1" in result.stderr
    assert "django.contrib.sessions.backends.signed_cookies" not in result.stderr
    assert "django.contrib.messages.storage.cookie.CookieStorage" not in result.stderr
