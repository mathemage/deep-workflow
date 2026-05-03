#!/usr/bin/env bash
set -euo pipefail

vercel_environment="${VERCEL_ENV:-local}"
vercel_runtime="${VERCEL:-}"
admin_database_url="${DATABASE_ADMIN_URL:-}"

if [[ "$vercel_environment" == "preview" || "$vercel_environment" == "production" || "$vercel_environment" == "development" || "$vercel_runtime" == "1" || "$vercel_runtime" == "true" ]]; then
  if [[ -z "${DJANGO_SECRET_KEY:-}" ]]; then
    echo "DJANGO_SECRET_KEY is required for Vercel ${vercel_environment} builds. Add it to that environment in Vercel project settings, then redeploy." >&2
    exit 1
  fi
  if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "DATABASE_URL is required for Vercel ${vercel_environment} builds. Add it to that environment in Vercel project settings, then redeploy." >&2
    exit 1
  fi
fi

if [[ "$vercel_environment" == "preview" || "$vercel_environment" == "production" || "$vercel_environment" == "development" || "$vercel_runtime" == "1" || "$vercel_runtime" == "true" ]]; then
  python manage.py check_database
fi

python manage.py collectstatic --noinput

if [[ "${VERCEL_RUN_MIGRATIONS:-0}" == "1" ]]; then
  if [[ -n "$admin_database_url" ]]; then
    echo "Using DATABASE_ADMIN_URL for migration-time database checks and migrations."
    DATABASE_URL="$admin_database_url" python manage.py check_database
    DATABASE_URL="$admin_database_url" python manage.py migrate --noinput
  else
    python manage.py migrate --noinput
  fi
else
  echo "Skipping migrations for ${VERCEL_ENV:-local} deployment. Set VERCEL_RUN_MIGRATIONS=1 to enable them explicitly."
fi
