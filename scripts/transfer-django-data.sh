#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${SOURCE_DATABASE_URL:-}" ]]; then
  echo "SOURCE_DATABASE_URL is required. Point it at the current SQLite or PostgreSQL database you want to export." >&2
  exit 1
fi

if [[ -z "${TARGET_DATABASE_URL:-}" ]]; then
  echo "TARGET_DATABASE_URL is required. Point it at the PostgreSQL database you want to import into." >&2
  exit 1
fi

fixture_file="$(mktemp "${TMPDIR:-/tmp}/deep-workflow-transfer.XXXXXX.json")"

cleanup() {
  rm -f "$fixture_file"
}

trap cleanup EXIT

echo "Checking source database connectivity."
DATABASE_URL="$SOURCE_DATABASE_URL" python manage.py check_database

echo "Exporting Django data from source database."
DATABASE_URL="$SOURCE_DATABASE_URL" python manage.py dumpdata \
  --exclude admin.logentry \
  --exclude auth.permission \
  --exclude contenttypes \
  --exclude sessions \
  --natural-foreign \
  --natural-primary \
  > "$fixture_file"

echo "Checking target database connectivity."
DATABASE_URL="$TARGET_DATABASE_URL" python manage.py check_database

echo "Applying migrations to target database."
DATABASE_URL="$TARGET_DATABASE_URL" python manage.py migrate --noinput

echo "Importing Django data into target database."
DATABASE_URL="$TARGET_DATABASE_URL" python manage.py loaddata "$fixture_file"
