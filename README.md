# deep-workflow

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://choosealicense.com/licenses/agpl-3.0/)

`deep-workflow` is a modern Python-based web app for tracking focused 45-minute deep-work sessions and daily rituals. It is designed for personal productivity, syncs across devices, and centers each day around three personal sessions plus one admin or must-do session. Licensed under the AGPLv3.

## Product idea

The project starts from a spreadsheet-inspired workflow, but the goal is a hosted web app that feels purpose-built for deep work rather than a manual logbook.

The core experience should work well on both laptops and smartphones:

- plan three personal deep-work sessions per day
- reserve a fourth session for admin, must-dos, or work for others
- default each session to 45 minutes
- keep goals, notes, and progress synced across devices

## MVP

The first version should focus on a clean, dependable foundation:

- authenticated access to the same account from multiple devices
- a daily sheet showing three personal sessions and one admin session
- session goals, notes, and completion state
- a server-backed 45-minute timer that survives refreshes
- daily and weekly progress summaries

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
