# deep-workflow

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://choosealicense.com/licenses/agpl-3.0/)

`deep-workflow` is a hosted Python-based web app for planning and completing focused 45-minute deep-work sessions. It replaces a spreadsheet-style ritual with a calmer daily sheet that stays in sync across laptops and phones. Licensed under the AGPLv3.

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
- a timezone-aware daily sheet showing three personal sessions and one admin session
- session goals, notes, and completion state
- a server-backed 45-minute timer that survives refreshes and device switching
- daily and weekly progress summaries
- a responsive web experience first, with PWA polish later

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

This keeps the app strongly Python-first while still leaving room for a modern, responsive UI. For the detailed hosting roadmap and deployment expectations, see `plan.md`, especially PR 9.

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
