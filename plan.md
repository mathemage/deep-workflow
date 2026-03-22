# deep-workflow roadmap

## Problem

Build a hosted, modern, mobile-friendly web app that replaces a spreadsheet for tracking daily focus rituals:

- 3 personal deep-work / flow sessions per day
- 1 admin / must-do session per day
- each session defaults to 45 minutes
- data must stay synced across laptops and phones
- the first version should be easy to build and iterate on with GitHub Copilot CLI

## Proposed approach

Recommended stack for v1:

- Django for the core web framework
- PostgreSQL for hosted persistence
- Django templates + HTMX + Alpine.js for a modern UX without a heavy SPA
- Tailwind CSS for responsive, polished UI
- Vercel for production hosting and pull request preview deployments

Why this stack:

- Django gives auth, ORM, migrations, admin, forms, and deployment maturity out of the box
- server-rendered pages keep the product simple while still feeling fast
- HTMX/Alpine add interactivity where needed without creating a separate frontend app
- PostgreSQL makes hosted sync straightforward
- Vercel gives a clear path for production releases and PR previews

Assumptions for MVP:

- single-user or very small-account setup first
- timezone-aware daily sheets
- start with responsive web, then add PWA polish
- timer state is server-backed via timestamps so refreshes and device switching stay accurate

## PR roadmap

### PR 1

- **Title:** `docs(product): Define MVP and architecture for deep-workflow`
- **Branch:** `docs/mvp-architecture`
- **Goal:** lock the product shape and technical direction before code generation starts
- **PR body:**

  ```md
  ## Why

  This project is starting from a lightweight README and a spreadsheet-inspired concept. We need a shared MVP definition and a technical direction that keeps future PRs small and reviewable.

  ## What changed

  - added a product brief for the deep-workflow app
  - defined MVP scope, non-goals, and success criteria
  - documented the recommended stack: Django + PostgreSQL + HTMX/Alpine + Tailwind
  - captured the phased PR roadmap for implementation

  ## Acceptance criteria

  - the repository clearly explains what the app does
  - MVP scope and non-goals are written down
  - the implementation roadmap is explicit enough to drive follow-up PRs

  ## Out of scope

  - application code
  - deployment setup
  ```

- **Prompt for GitHub Copilot:**

  ```text
  Read README.md and .github/copilot-instructions.md first.

  Create a new GitHub Issue for defining the product brief and technical direction for the hosted deep-workflow web app. Then create a branch named docs/mvp-architecture and implement only this PR.

  Add or update documentation to define:
  - the product vision
  - MVP scope
  - non-goals
  - user flows for 3 personal sessions + 1 admin session per day
  - recommended stack: Django, PostgreSQL, Django templates, HTMX/Alpine, Tailwind
  - the staged PR roadmap

  Keep the PR documentation-only and easy to review. Use commit messages that match the repo rules, with an explicit scope and the issue number.

  Open a PR with the title:
  docs(product): Define MVP and architecture for deep-workflow

  Use the planned PR body from the roadmap.
  ```

### PR 2

- **Title:** `chore(app): Bootstrap Django project, tooling, and CI`
- **Branch:** `chore/bootstrap-django`
- **Goal:** create a clean local/dev foundation that future feature PRs can build on
- **PR body:**

  ```md
  ## Why

  Before shipping product features, we need a reliable project skeleton, dependency management, local development workflow, and automated checks.

  ## What changed

  - scaffolded the Django project and app structure
  - added dependency management and environment configuration
  - wired PostgreSQL for local and hosted environments
  - added lint/test/format tooling and GitHub Actions CI
  - added a simple base layout and health endpoint

  ## Acceptance criteria

  - the app starts locally with documented setup steps
  - CI runs tests and basic quality checks
  - the repository has a clear foundation for follow-up feature PRs

  ## Out of scope

  - authentication UX
  - domain models for sessions
  ```

- **Prompt for GitHub Copilot:**

  ```text
  Read README.md and .github/copilot-instructions.md first.

  Create a new GitHub Issue for bootstrapping the app foundation, then create branch chore/bootstrap-django and implement only this PR.

  Scaffold a Django-based web app with:
  - PostgreSQL-ready settings
  - environment-based config
  - a simple base template and homepage
  - linting, tests, and CI
  - setup docs for local development

  Keep the scope foundational only. Do not add business features yet. Add or update tests and docs where appropriate. Use scoped commit messages with the issue number, then open the PR with the planned title and body.
  ```

### PR 3

- **Title:** `feat(auth): Add authentication and user preferences`
- **Branch:** `feat/auth-preferences`
- **Goal:** make the hosted app usable across devices under a real account
- **PR body:**

  ```md
  ## Why

  A hosted app needs authentication and basic user settings before personal tracking data can be safely synced across devices.

  ## What changed

  - added login/logout flows
  - added user profile/preferences for timezone and default session duration
  - protected app routes behind authentication
  - documented the authentication flow for local and hosted usage

  ## Acceptance criteria

  - a user can sign in and sign out
  - timezone and default duration can be saved per user
  - protected pages require authentication

  ## Out of scope

  - session tracking data model
  - timer UX
  ```

- **Prompt for GitHub Copilot:**

  ```text
  Read README.md and .github/copilot-instructions.md first.

  Create a new GitHub Issue for authentication and preferences, then create branch feat/auth-preferences and implement only this PR.

  Add Django authentication and the minimum user settings needed for this app:
  - login/logout
  - protected routes
  - timezone preference
  - default session duration preference, defaulting to 45 minutes

  Keep the UX simple and production-minded. Add tests for auth and preferences. Update docs as needed. Use scoped commit messages with the issue number, then open the PR with the planned title and body.
  ```

### PR 4

- **Title:** `feat(model): Add daily sheet and work session domain models`
- **Branch:** `feat/session-models`
- **Goal:** introduce the data model that powers the spreadsheet replacement
- **PR body:**

  ```md
  ## Why

  We need durable domain objects for daily sheets and timed sessions before building the main UI.

  ## What changed

  - added models for daily sheets and work sessions
  - encoded session type/category for personal vs admin
  - added status fields and timestamps needed for timer state
  - added migrations and admin registration

  ## Acceptance criteria

  - the data model supports 3 personal sessions and 1 admin session per day
  - models are migration-backed and test-covered
  - the schema is ready for CRUD and timer features

  ## Out of scope

  - polished end-user UI
  - timer countdown behavior
  ```

- **Prompt for GitHub Copilot:**

  ```text
  Read README.md and .github/copilot-instructions.md first.

  Create a new GitHub Issue for the core data model, then create branch feat/session-models and implement only this PR.

  Add Django models and migrations for:
  - a daily sheet / daily plan entity
  - work sessions belonging to a day
  - session category: personal or admin
  - status fields such as planned, active, completed, skipped
  - timestamps needed for future timer behavior
  - optional notes and goal text

  Register the models in Django admin and add model tests. Keep this PR focused on backend/domain structure, not UI polish. Use scoped commit messages with the issue number, then open the PR with the planned title and body.
  ```

### PR 5

- **Title:** `feat(sheet): Build the responsive daily sheet UI`
- **Branch:** `feat/daily-sheet-ui`
- **Goal:** deliver the first real spreadsheet replacement view
- **PR body:**

  ```md
  ## Why

  Once the data model exists, the next most important step is a usable daily screen that works well on both laptop and phone.

  ## What changed

  - added the main daily sheet page
  - rendered 3 personal session cards and 1 admin session card for a selected day
  - added create/edit interactions for goals, notes, and status
  - made the layout responsive for mobile and desktop

  ## Acceptance criteria

  - a signed-in user can view today’s sheet
  - session cards are easy to use on small screens
  - goals, notes, and status can be edited without admin access

  ## Out of scope

  - live countdown timer
  - reporting dashboards
  ```

- **Prompt for GitHub Copilot:**

  ```text
  Read README.md and .github/copilot-instructions.md first.

  Create a new GitHub Issue for the daily sheet UI, then create branch feat/daily-sheet-ui and implement only this PR.

  Build the main authenticated UI for the app:
  - a daily sheet page focused on today by default
  - four session slots: 3 personal, 1 admin
  - responsive card-based layout for desktop and mobile
  - create/edit flows for session goal, notes, and status

  Use Django templates plus HTMX/Alpine only where they genuinely improve UX. Keep this PR focused on CRUD and layout, not timer logic. Add tests and update docs as needed. Use scoped commit messages with the issue number, then open the PR with the planned title and body.
  ```

### PR 6

- **Title:** `feat(timer): Add synced 45-minute session timer and state transitions`
- **Branch:** `feat/synced-session-timer`
- **Goal:** make the app feel purpose-built for deep work instead of a static tracker
- **PR body:**

  ```md
  ## Why

  The core differentiator from a plain spreadsheet is a timer workflow that survives refreshes and device switches.

  ## What changed

  - added start/pause/complete behavior for sessions
  - added server-backed timing based on timestamps instead of local-only browser state
  - showed remaining time in the daily sheet UI
  - handled refresh and multi-device continuity for active sessions

  ## Acceptance criteria

  - a session can be started and completed from the daily sheet
  - remaining time stays accurate after refresh
  - the timer reflects server truth instead of only browser-local state

  ## Out of scope

  - advanced analytics
  - background notifications
  ```

- **Prompt for GitHub Copilot:**

  ```text
  Read README.md and .github/copilot-instructions.md first.

  Create a new GitHub Issue for the synced timer flow, then create branch feat/synced-session-timer and implement only this PR.

  Add the timer workflow for 45-minute sessions:
  - start, pause if needed, resume if needed, and complete transitions
  - server-backed timestamps so the timer survives refreshes and switching devices
  - UI feedback on the daily sheet for an active session and remaining time

  Do not add websockets unless clearly necessary; prefer a simpler approach that keeps server truth authoritative. Add tests for state transitions and time calculations. Use scoped commit messages with the issue number, then open the PR with the planned title and body.
  ```

### PR 7

- **Title:** `feat(rules): Auto-generate daily sheets and add progress summaries`
- **Branch:** `feat/daily-rules-summary`
- **Goal:** turn the tracker into a habit system instead of a manual logbook
- **PR body:**

  ```md
  ## Why

  The product should reflect the intended routine automatically: 3 personal sessions and 1 admin session each day, with visible progress.

  ## What changed

  - auto-generated daily sheets with default session slots
  - enforced the 3 personal + 1 admin default structure
  - added daily and weekly completion summaries
  - added streak/progress indicators for consistency

  ## Acceptance criteria

  - opening a new day creates the expected default structure
  - users can see daily and weekly completion progress
  - summary calculations are tested and timezone-aware

  ## Out of scope

  - CSV import/export
  - PWA installation
  ```

- **Prompt for GitHub Copilot:**

  ```text
  Read README.md and .github/copilot-instructions.md first.

  Create a new GitHub Issue for daily sheet automation and summaries, then create branch feat/daily-rules-summary and implement only this PR.

  Add product rules and reporting:
  - automatically create a day with 3 personal session slots and 1 admin slot
  - ensure the daily view always has that default structure
  - add daily and weekly completion summaries
  - add simple streak/progress indicators

  Keep this PR focused on automation and summaries. Do not mix in PWA or deployment work. Add tests for timezone-sensitive day generation and summary calculations. Use scoped commit messages with the issue number, then open the PR with the planned title and body.
  ```

### PR 8

- **Title:** `feat(mobile): Polish the smartphone UX and add PWA basics`
- **Branch:** `feat/mobile-pwa`
- **Goal:** make the app feel great on phones, not just acceptable
- **PR body:**

  ```md
  ## Why

  The app is intended for use from laptops and smartphones, so mobile experience is a core product requirement rather than a nice-to-have.

  ## What changed

  - improved mobile-first layout and spacing
  - added touch-friendly interactions and navigation
  - added PWA basics such as manifest and installable shell
  - improved loading states and general UI polish

  ## Acceptance criteria

  - the main workflows are comfortable on phone-sized screens
  - the app can be installed as a PWA
  - the UX feels modern and intentional across devices

  ## Out of scope

  - deployment automation
  - complex offline-first sync
  ```

- **Prompt for GitHub Copilot:**

  ```text
  Read README.md and .github/copilot-instructions.md first.

  Create a new GitHub Issue for mobile UX and PWA polish, then create branch feat/mobile-pwa and implement only this PR.

  Improve the app for smartphones:
  - make the main daily sheet experience clearly mobile-first
  - improve spacing, typography, and touch targets
  - add PWA essentials such as a manifest and installable experience
  - keep the implementation simple and reliable

  Avoid turning this into a broad redesign. Focus on the existing key flows and make them feel excellent on phones. Add tests where appropriate and update docs as needed. Use scoped commit messages with the issue number, then open the PR with the planned title and body.
  ```

### PR 9

- **Title:** `chore(deploy): Prepare production deployment, backups, and monitoring`
- **Branch:** `chore/production-deploy`
- **Goal:** make the app safely hostable and maintainable
- **PR body:**

  ```md
  ## Why

  A synced personal web app only becomes useful once it can be deployed reliably and operated with confidence.

  ## What changed

  - added production settings and Vercel deployment configuration
  - documented the Vercel hosting path for production and PR previews
  - added health checks and baseline monitoring hooks
  - documented database backup/restore expectations

  ## Acceptance criteria

  - the repository documents a clear Vercel deployment path for production and PR previews
  - production configuration is separated from local development
  - backup and restore steps are defined

  ## Out of scope

  - new product features
  - advanced analytics
  ```

- **Prompt for GitHub Copilot:**

  ```text
  Read README.md and .github/copilot-instructions.md first.

  Create a new GitHub Issue for deployment readiness, then create branch chore/production-deploy and implement only this PR.

  Prepare the app for real hosting:
  - production-safe Django settings
  - deployment config for Vercel production and PR preview environments
  - health checks
  - monitoring/logging hooks
  - backup and restore documentation for PostgreSQL

  Keep this PR operational in scope. Do not add new end-user features. Update docs thoroughly, add validation where possible, and use scoped commit messages with the issue number before opening the PR with the planned title and body.
  ```

## Notes

- If you want an even smaller first slice, split PR 2 into separate setup and CI PRs.
- If spreadsheet import becomes important, add a later PR for CSV import/export after PR 7.
- The roadmap intentionally reaches a solid single-user hosted MVP on Vercel before considering multi-user or collaboration features.
