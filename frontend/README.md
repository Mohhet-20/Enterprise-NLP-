# Frontend

React 18 + TypeScript, Vite 8, Tailwind, Radix/shadcn-style primitives, TanStack Query,
Zustand, Recharts and Framer Motion, wired to the API in `../backend`.

## Pages

| Page | What it does |
|---|---|
| **Playground** | Run any served task on one text or a batch of up to 64; zero-shot labels and similarity pairs are entered inline; **Explain** renders Integrated Gradients word attributions as a heatmap |
| **Dashboard** | Live KPIs (datasets, models, deployments, evaluations), accuracy trend, system status |
| **Datasets** | Create, upload CSV with a live validation report, profile charts, version history, archive/restore |
| **Models** | Model Registry: register, approve/reject (role-gated), promote, deploy, champion |
| **Evaluations** | Run the served model or the lexicon baseline on SST-2, the challenge set, or an uploaded dataset; per-run confusion matrix, per-class metrics, calibration, misclassified samples, Markdown/CSV export |

Sidebar items for features that don't exist yet are marked "soon" and route to a
placeholder page.

## Quickstart

```bash
npm install
cp .env.example .env       # VITE_API_BASE_URL, defaults to http://localhost:8000/api/v1
npm run dev                # http://localhost:5173
```

Start the backend first (`uvicorn backend.main:app --reload` from the repo root). In
development it seeds an `admin` / `ChangeMe123!` account; you can also register a new
account from the login page (new accounts start read-only).

## Scripts

```bash
npm run lint       # eslint
npm test           # vitest + Testing Library (jsdom)
npm run build      # tsc -b && vite build -> dist/
```

## Design

See `../docs/design-notes.md`. In short: a deep teal primary for the "confidence"
metaphor, warm amber/brick for warning and negative states, Space Grotesk for display
type, IBM Plex Sans for body text and IBM Plex Mono for anything that is model output
(tokens, labels, scores). Light and dark themes share one token set in `src/index.css`.
