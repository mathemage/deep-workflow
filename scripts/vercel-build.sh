#!/usr/bin/env bash
set -euo pipefail

vercel_environment="${VERCEL_ENV:-local}"
vercel_runtime="${VERCEL:-}"

if [[ "$vercel_environment" == "preview" || "$vercel_environment" == "production" || "$vercel_environment" == "development" || "$vercel_runtime" == "1" || "$vercel_runtime" == "true" ]]; then
  if [[ -z "${DJANGO_SECRET_KEY:-}" ]]; then
    echo "DJANGO_SECRET_KEY is required for Vercel ${vercel_environment} builds. Add it to that environment in Vercel project settings, then redeploy." >&2
    exit 1
  fi
fi

python manage.py collectstatic --noinput

if [[ "${VERCEL_RUN_MIGRATIONS:-0}" == "1" ]]; then
  python manage.py migrate --noinput
else
  echo "Skipping migrations for ${VERCEL_ENV:-local} deployment. Set VERCEL_RUN_MIGRATIONS=1 to enable them explicitly."
fi
