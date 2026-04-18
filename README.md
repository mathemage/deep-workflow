# deep-workflow

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://choosealicense.com/licenses/agpl-3.0/)

`deep-workflow` is a hosted Django-based web app for planning and completing focused 45-minute deep-work sessions. It replaces a spreadsheet-style ritual with a calmer daily sheet that stays in sync across laptops and phones. Licensed under the AGPL v3.

## Product vision

The project starts from a spreadsheet-inspired workflow, but the goal is a hosted web app that feels purpose-built for deep work rather than a manual logbook.

The core experience should work well on both laptops and smartphones:

- plan three personal deep-work sessions per day
- reserve a fourth session for admin, must-dos, or work for others
- default each session to 45 minutes
- keep goals, notes, and progress synced across devices

The app should stay calm, low-friction, and clearly focused on the next meaningful action instead of growing into a generic project-management tool.

## MVP scope

The first version should focus on a clean, dependable foundation:

- authenticated access to the same account from multiple devices
- a timezone-aware daily sheet, generated and displayed using each user's configured timezone, showing three personal sessions and one admin session
- session goals, notes, and completion state
- a 45-minute session timer whose start time and state are stored on the server so it survives refreshes and device switching
- daily and weekly progress summaries
- a responsive web experience that works well on phones and laptops, with installable PWA basics

## Non-goals

The initial release should not try to do everything:

- team collaboration or shared planning workflows
- complex project-management features such as boards, task trees, or backlog systems
- advanced analytics beyond lightweight daily and weekly summaries
- offline-first sync or native mobile apps in v1

## Daily workflow

The intended daily flow is simple:

1. Sign in and open today's sheet on a laptop or phone.
2. See four session slots for the day: three personal sessions and one admin session.
3. Add or update the goal and notes for the next session, then start the timer when ready.
4. Move each session through planned, active, completed, or skipped states as the day unfolds.
5. Review daily and weekly progress to keep the routine consistent.

## Success criteria

The MVP is successful when:

- the repository clearly explains the app and the daily routine it supports
- a user can plan and track the 3 personal + 1 admin structure from one account across devices
- timer state stays accurate after refreshes and device switching
- the product stays simpler and calmer than a general-purpose productivity app

## Recommended v1 stack

To keep the first version simple and fast to iterate on, the recommended stack is:

- Django
- PostgreSQL
- Django templates with HTMX and Alpine.js
- Tailwind CSS
- Vercel for production hosting and pull request preview deployments

This keeps the app strongly Python-first while still leaving room for a modern, responsive UI. For the detailed hosting roadmap and deployment expectations, see `plan.md`, especially roadmap item 9.

## Roadmap

The implementation should land in small, reviewable PRs:

1. define the MVP and architecture
2. bootstrap the Django app, tooling, and CI
3. add authentication and user preferences
4. add daily sheet and work session domain models
5. build the responsive daily sheet UI
6. add the synced 45-minute session timer
7. auto-generate daily sheets and add progress summaries
8. polish the mobile UX and add PWA basics
9. prepare Vercel deployment, backups, and monitoring

## Current foundation

This repository now includes the foundation plus roadmap slices 1 through 9:

- Django project and `core` app wiring
- environment-based settings with `DATABASE_URL` support for PostgreSQL
- login/logout with protected app routes
- per-user timezone and default session duration settings
- daily sheet and work session domain models with migrations, admin registration, and tests
- a responsive daily sheet UI with previous/next day navigation plus per-session goal and notes editing
- a server-backed session timer with start, pause, resume, and complete actions plus remaining-time feedback
- auto-generated daily sheets that keep the fixed 3 personal + 1 admin structure intact
- daily and weekly progress summaries with simple streak and completion indicators
- mobile-first layout polish for the daily sheet, navigation, and touch targets
- a manifest, service worker, and installable PWA shell
- production-hardened hosted settings, Vercel deployment config, readiness endpoints, and request-ID-aware logging
- PostgreSQL backup and restore documentation for hosted operations
- Ruff linting/formatting, pytest-based tests, and GitHub Actions CI

## Local development

Prerequisites:

- Python 3.12.x
- PostgreSQL 16+ if you want local PostgreSQL instead of the default SQLite fallback

Bootstrap the project:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The app will be available at `http://127.0.0.1:8000/`. Sign in at `http://127.0.0.1:8000/login/`, then use the daily sheet to plan, update, and run the four session cards with the synced timer. On supported browsers, the app also exposes an install prompt backed by `http://127.0.0.1:8000/manifest.webmanifest` and `http://127.0.0.1:8000/service-worker.js`. The settings page still lets you choose your timezone and default session duration. Health endpoints remain available at `http://127.0.0.1:8000/health/`, `http://127.0.0.1:8000/health/live/`, and `http://127.0.0.1:8000/health/ready/`.

### PostgreSQL configuration

The settings are driven by environment variables and switch to PostgreSQL automatically when `DATABASE_URL` is set. For local PostgreSQL development, create a database and update `.env` with a URL such as:

```bash
createdb deep_workflow
```

```env
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/deep_workflow
```

If `DATABASE_URL` is omitted, Django falls back to SQLite for the quickest local bootstrap.

## Vercel deployment

The repository now includes the files needed to host the app on Vercel production and PR preview environments:

- `wsgi.py` exposes the Django WSGI app through Vercel's Python runtime
- `.python-version` pins Vercel to Python 3.12, matching the project's supported local Python 3.12.x runtime
- `vercel.json` sets the Vercel build command and rewrites
- `scripts/vercel-build.sh` requires `DJANGO_SECRET_KEY` and `DATABASE_URL` for hosted builds, verifies database readiness, always runs `collectstatic`, and only runs migrations when `VERCEL_RUN_MIGRATIONS=1`
- hosted settings derive trusted hosts and CSRF origins from `APP_BASE_URL` plus Vercel's runtime URLs, then enable HTTPS redirects, secure cookies, conservative HSTS defaults, WhiteNoise static serving, and request-ID-aware logging

### Required environment variables

| Variable | Production | Preview | Notes |
| --- | --- | --- | --- |
| `DJANGO_SECRET_KEY` | Required | Required | Use a unique secret per environment. Hosted builds fail fast until this is set. |
| `DATABASE_URL` | Required | Required | Point previews at an isolated PostgreSQL database or branch database, not production. |
| `APP_BASE_URL` | `https://deep-workflow.vercel.app` | Optional | Sets the canonical production URL and anchors the production host/origin configuration. |
| `DJANGO_ENABLE_HOSTED_SQLITE_FALLBACK` | Emergency only | Emergency only | Leave unset for normal deploys. Set to `1` only when intentionally activating the temporary hosted SQLite recovery mode. |
| `DJANGO_SECURE_HSTS_PRELOAD` | Optional | Optional | Leave unset unless you intentionally want preload and already satisfy the preload requirements (`includeSubDomains` plus at least `31536000` seconds). |
| `VERCEL_RUN_MIGRATIONS` | Set to `1` only for deliberate schema rollouts | Set to `1` only for isolated preview databases | Build-time migrations are always opt-in. |

#### Generate and add `DJANGO_SECRET_KEY`

1. Generate a secret locally:

   ```bash
   . .venv/bin/activate
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

2. Copy the printed value. Do not commit it or save it in the repository.
3. In Vercel, open the `deep-workflow` project, then go to **Settings** -> **Environment Variables**.
4. Create `DJANGO_SECRET_KEY` for the **Preview** environment and paste the copied value.
5. Generate a second secret the same way and create `DJANGO_SECRET_KEY` for the **Production** environment.
6. Save the variables and redeploy if a build already failed because the secret was missing.

Vercel injects `VERCEL_ENV`, `VERCEL_URL`, `VERCEL_BRANCH_URL`, and `VERCEL_PROJECT_PRODUCTION_URL` automatically. The app uses those values to allow the current production deployment and each preview deployment without widening `ALLOWED_HOSTS` to every `*.vercel.app` hostname.

### Production and preview workflow

1. Connect the repository to Vercel and keep `main` as the production branch.
2. Set `APP_BASE_URL=https://deep-workflow.vercel.app` in the Production environment.
3. Set `DJANGO_SECRET_KEY` and `DATABASE_URL` in both Production and Preview. Use a separate preview database if you want preview deployments to run migrations.
4. Let pushes to non-`main` branches create Preview deployments automatically. Leave `VERCEL_RUN_MIGRATIONS` unset for normal deploys; only turn it on for isolated preview databases or a coordinated production schema rollout, then redeploy intentionally.
5. After each deployment, check `GET /health/ready/` for database readiness and `GET /health/live/` for the lightweight liveness probe.

#### Emergency hosted SQLite recovery

Normal hosted deploys should continue to fail fast if `DATABASE_URL` is missing or broken. If you need a temporary outage recovery mode, you can opt into the hosted SQLite fallback by setting `DJANGO_ENABLE_HOSTED_SQLITE_FALLBACK=1` alongside a SQLite `DATABASE_URL`.

This mode is for emergency recovery only. It moves sessions and flash messages to signed cookies so the app can run from a bundled SQLite snapshot on Vercel, but it should not replace the normal PostgreSQL-backed production path. Only use it when your session and message payloads are small enough to fit within browser cookie limits, and do not treat the cookie contents as secret: signed cookies are tamper-resistant, but their contents remain readable by the client.

### Health checks and monitoring hooks

- `GET /health/live/` is a cheap liveness probe that does not touch the database.
- `GET /health/ready/` checks database connectivity and returns HTTP `503` when the database is unavailable.
- `GET /health/` remains a readiness alias for simple uptime integrations.
- Health responses include the deployment environment and, when Vercel provides them, the deployment URL and git SHA.
- Responses include an `X-Request-ID` response header, and the default log format writes `request_id=... env=...` to stdout so Vercel logs and log drains can correlate failures quickly.

## PostgreSQL backup and restore

Take backups outside Vercel with PostgreSQL client tools and store them in durable storage that is separate from the app deployment.

Create a compressed backup:

```bash
mkdir -p backups
pg_dump \
  --format=custom \
  --no-owner \
  --no-privileges \
  --file "backups/deep_workflow_$(date +%F_%H%M%S).dump" \
  "$DATABASE_URL"
```

Verify a backup by restoring it into a disposable database first:

```bash
createdb deep_workflow_restore_check
pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  --dbname=deep_workflow_restore_check \
  backups/deep_workflow_2026-04-05_180000.dump
```

Restore into a replacement hosted database before cutting production over:

```bash
pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  --dbname="$RESTORE_DATABASE_URL" \
  backups/deep_workflow_2026-04-05_180000.dump
```

Prefer restoring into a fresh database, smoke-test the app with `/health/ready/`, and only then swap the production `DATABASE_URL`. That keeps rollback simple and avoids destructive restore work against the live database.

## Quality checks

Run the foundational checks before opening a change:

```bash
. .venv/bin/activate
ruff check .
ruff format --check .
python manage.py check
pytest
```

For a production-leaning settings smoke test, also run:

```bash
. .venv/bin/activate
APP_BASE_URL=https://deep-workflow.vercel.app \
DJANGO_DEBUG=False \
DJANGO_SECRET_KEY=local-deploy-check-only-1234567890-abcdefghijklmnopqrstuvwxyz \
python manage.py check --deploy
```

CI runs the same lint and test commands against PostgreSQL on every push and pull request, and it now also runs `python manage.py check --deploy`.
