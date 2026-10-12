# Frontend — Enterprise NLP Intelligence Platform

React + TypeScript + Tailwind + shadcn/ui-style primitives, wired to the
real backend in `../backend`.

## Status: App Shell + Inference Playground

This build implements two things fully, end to end, against the live API:

- **App shell** — sidebar, top nav, breadcrumbs, theme toggle (light/dark,
  persisted), command palette (⌘K / Ctrl+K), user menu, dev-mode login/logout,
  live system-status indicator (real `/health` polling).
- **Inference Playground** — task selector driven by the backend's actual
  plugin registry (`GET /tasks`), single-text prediction against
  `POST /predict`, confidence visualization (the "confidence chip" signature
  component + a Recharts label-distribution bar chart), session prediction
  history, and honest error states (a `ModelLoadError` from the backend
  because `transformers`/`torch` aren't installed there yet shows a clear
  explanation, not a stack trace).

Every other sidebar item (Overview, Models, Datasets, Monitoring, Admin,
Copilot) is visibly marked "soon" and routes to a plain "not built yet"
page — nothing is faked.

## Quickstart

```bash
npm install
cp .env.example .env       # points at the backend; edit if it's not on :8000
npm run dev                # http://localhost:5173
```

Make sure the backend is running (`../backend`, `uvicorn backend.main:app --reload`)
with `ALLOWED_ORIGINS` including `http://localhost:5173` (it does, by default).

Sign in with any username — the backend's `/auth/login` is dev-mode only
(no password store exists yet) and issues a real JWT based on the role you pick.

## Build

```bash
npm run build      # tsc -b && vite build -> dist/
npm run preview    # serve the production build locally
```

## Design tokens

See `../docs/design-notes.md` for the color/type/signature rationale.
Short version: a deep signal-teal primary (the "confidence" metaphor),
warm amber/brick semantic colors for warning/negative states, Space
Grotesk for display type, IBM Plex Sans for body, IBM Plex Mono for
anything that represents model output (tokens, labels, scores) — chosen
deliberately to avoid the generic cream+terracotta / near-black+neon
AI-product defaults.

## What's not built yet

Batch/CSV/JSON upload, token-level explanation, attention visualization,
embedding explorer, dataset management, experiment dashboard, monitoring
dashboard, human review, reporting/export, admin dashboard, AI copilot,
enterprise search, workflow center, and MFA/registration/password-reset
flows are all out of scope for this pass — see the sidebar's "soon" badges
and `docs/architecture-guide.md` for what's next.
