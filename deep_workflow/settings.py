"""Django settings for the deep_workflow project."""

import os
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

from .deployment import (
    build_allowed_hosts,
    build_csrf_trusted_origins,
    canonical_deployment_url,
    default_debug,
    deployment_environment,
    deployment_git_sha,
    hosted_environment,
    hsts_preload_enabled,
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(BASE_DIR / ".env")
DEFAULT_DEBUG = default_debug(os.environ)

env = environ.Env(
    APP_BASE_URL=(str, ""),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1", "testserver"]),
    DJANGO_CSRF_TRUSTED_ORIGINS=(
        list,
        ["http://localhost:8000", "http://127.0.0.1:8000"],
    ),
    DJANGO_DB_CONN_MAX_AGE=(int, 60),
    DJANGO_DB_SSL_MODE=(str, "require"),
    DJANGO_DEBUG=(bool, DEFAULT_DEBUG),
    DJANGO_LOG_LEVEL=(str, "DEBUG" if DEFAULT_DEBUG else "INFO"),
    DJANGO_REQUEST_LOG_LEVEL=(str, "WARNING"),
    DJANGO_SECRET_KEY=(str, "unsafe-local-development-key"),
    DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=(bool, True),
    DJANGO_SECURE_HSTS_PRELOAD=(bool, False),
    DJANGO_SECURE_HSTS_SECONDS=(int, 3600),
    DJANGO_SECURE_PROXY_SSL_HEADER_NAME=(str, "HTTP_X_FORWARDED_PROTO"),
    DJANGO_SECURE_PROXY_SSL_HEADER_VALUE=(str, "https"),
    DJANGO_SECURE_REFERRER_POLICY=(str, "strict-origin-when-cross-origin"),
    DJANGO_STATIC_MAX_AGE=(int, 31536000),
    DJANGO_USE_X_FORWARDED_HOST=(bool, True),
    DJANGO_X_FRAME_OPTIONS=(str, "DENY"),
    TIME_ZONE=(str, "UTC"),
)

DEBUG = env("DJANGO_DEBUG")
DEPLOYMENT_ENV = deployment_environment(os.environ)
HOSTED_ENV = not DEBUG and hosted_environment(os.environ)
DEPLOYMENT_URL = canonical_deployment_url(os.environ)
DEPLOYMENT_GIT_SHA = deployment_git_sha(os.environ)

SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = build_allowed_hosts(env.list("DJANGO_ALLOWED_HOSTS"), os.environ)
CSRF_TRUSTED_ORIGINS = build_csrf_trusted_origins(
    env.list("DJANGO_CSRF_TRUSTED_ORIGINS"),
    os.environ,
)

if not DEBUG and SECRET_KEY == "unsafe-local-development-key":
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY before disabling DJANGO_DEBUG.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.RequestIDMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.UserTimezoneMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "deep_workflow.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.csrf",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "deep_workflow.wsgi.application"


DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DJANGO_DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

if HOSTED_ENV and DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"].setdefault(
        "sslmode",
        env("DJANGO_DB_SSL_MODE"),
    )


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE")

USE_I18N = True
USE_TZ = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = env("DJANGO_SECURE_REFERRER_POLICY")
SECURE_SSL_REDIRECT = env.bool(
    "DJANGO_SECURE_SSL_REDIRECT",
    default=HOSTED_ENV,
)
SESSION_COOKIE_SECURE = env.bool(
    "DJANGO_SESSION_COOKIE_SECURE",
    default=HOSTED_ENV,
)
CSRF_COOKIE_SECURE = env.bool(
    "DJANGO_CSRF_COOKIE_SECURE",
    default=HOSTED_ENV,
)
SECURE_HSTS_SECONDS = env.int(
    "DJANGO_SECURE_HSTS_SECONDS",
    default=3600 if HOSTED_ENV else 0,
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=HOSTED_ENV,
)
HSTS_PRELOAD_OPT_IN = env.bool(
    "DJANGO_SECURE_HSTS_PRELOAD",
    default=False,
)
SECURE_HSTS_PRELOAD = hsts_preload_enabled(
    preload_opt_in=HSTS_PRELOAD_OPT_IN,
    secure_hsts_seconds=SECURE_HSTS_SECONDS,
    include_subdomains=SECURE_HSTS_INCLUDE_SUBDOMAINS,
)
USE_X_FORWARDED_HOST = env.bool(
    "DJANGO_USE_X_FORWARDED_HOST",
    default=HOSTED_ENV,
)
X_FRAME_OPTIONS = env("DJANGO_X_FRAME_OPTIONS")

if HOSTED_ENV:
    SECURE_PROXY_SSL_HEADER = (
        env("DJANGO_SECURE_PROXY_SSL_HEADER_NAME"),
        env("DJANGO_SECURE_PROXY_SSL_HEADER_VALUE"),
    )

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if HOSTED_ENV
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        )
    },
}
WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_MAX_AGE = env.int("DJANGO_STATIC_MAX_AGE")
WHITENOISE_USE_FINDERS = DEBUG

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

LOG_LEVEL = env("DJANGO_LOG_LEVEL").upper()
REQUEST_LOG_LEVEL = env("DJANGO_REQUEST_LOG_LEVEL").upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_context": {
            "()": "core.logging.RequestContextFilter",
        }
    },
    "formatters": {
        "standard": {
            "format": (
                "%(asctime)s %(levelname)s %(name)s "
                "request_id=%(request_id)s env=%(deployment_env)s %(message)s"
            )
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["request_context"],
            "formatter": "standard",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "core.health": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": REQUEST_LOG_LEVEL,
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": REQUEST_LOG_LEVEL,
            "propagate": False,
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
