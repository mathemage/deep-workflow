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
