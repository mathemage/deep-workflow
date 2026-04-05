#!/usr/bin/env bash
set -euo pipefail

python manage.py collectstatic --noinput

if [[ "${VERCEL_RUN_MIGRATIONS:-0}" == "1" ]]; then
  python manage.py migrate --noinput
else
  echo "Skipping migrations for ${VERCEL_ENV:-local} deployment. Set VERCEL_RUN_MIGRATIONS=1 to enable them explicitly."
fi
