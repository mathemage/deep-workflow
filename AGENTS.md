# Deep Workflow App - Agent Guide

## Business Requirements

- Help a user plan and complete three personal deep-work sessions and one admin or must-do session each day.
- Default each session to 45 minutes unless the product requirements explicitly change.
- Keep daily sheets, goals, notes, timer state, and progress synced across laptops and phones.
- Favor a calm, low-friction experience that supports focus instead of generic project-management complexity.
- Ship the hosted app with Vercel as the default target for production and pull request preview environments.

## Technical Details

- Follow the roadmap in `plan.md`: Django, PostgreSQL, Django templates with HTMX and Alpine.js, Tailwind CSS, and Vercel for hosting.
- Keep the timer server-backed via timestamps so refreshes and device switching do not lose session state.
- Prefer server-rendered flows and simple abstractions; only add client-side behavior where it materially improves the experience.
- Cover core workflow logic and persistence with automated tests, and use integration or end-to-end tests for critical user flows.
- Keep documentation concise and consistent across `README.md`, `plan.md`, and this file when product or hosting assumptions change.

## UX Guidance

- Use a low-distraction, mobile-friendly interface that works well on both laptops and phones.
- Make the next important action obvious: planning a session, starting the timer, updating notes, or marking work complete.
- Avoid visually noisy patterns, unnecessary animation, and clutter that would interrupt focus.
- Keep status, progress, and timing information clear and accessible.

## Strategy

1. Write a concrete implementation plan with success criteria for each phase, including project scaffolding, basic documentation, and rigorous testing.
2. Execute the plan in small, reviewable pull requests that keep scope tight and preserve momentum.
3. Carry out integration testing with Playwright or a similar tool for the most important end-to-end flows, fixing defects before calling the MVP done.
4. Only consider the MVP complete when the app is finished, tested, and ready to run for real users in the hosted environment.

## Coding standards

1. Use current stable libraries and idiomatic approaches that fit the repository's chosen stack.
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, and avoid unnecessary defensive programming or speculative features.
3. Be concise. Keep the README minimal, focused, and free of emojis.

# AI Coding Assistant Instructions

## Git and GitHub

- For every task, first create a new Issue, then create the related branch, and finally open the related PR.
- Use best practices for commit messages. Every commit message should follow this regex:
  `^(?:fix|chore|docs|feat|refactor|style|test)(?:\(.+\)): [A-Z].+(?:\s#\d+)?$`
- Always use one of the commit type keywords (`fix`, `chore`, `docs`, `feat`, `refactor`, `style`, `test`) with an explicit scope in the `type(scope): message` format (for example, `feat(api): Add new endpoint`).
