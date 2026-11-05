# Design Notes — Frontend

## Brief

An enterprise NLP platform frontend, comparable in polish to Databricks /
Hugging Face / Snowflake — for ML engineers running and inspecting model
predictions, not a consumer or marketing surface.

## Token system

**Color** (HSL, defined as CSS variables in `src/index.css`, light + dark):
- `primary` — deep signal-teal (`160 33% 26%` light / `160 35% 55%` dark).
  The core metaphor of the product is "confidence in a prediction," so the
  brand color is the same hue used for the confidence-fill on every result.
- `warning` — warm amber (`28 55% 48%`), reserved for caution states.
- `destructive` — muted brick red (`6 55% 42%`), reserved for errors/negative
  classifications — never used decoratively.
- `background`/`foreground` — a cool off-white paper tone in light mode, a
  deep blue-black (not pure black) in dark mode.

Deliberately not the cream+terracotta serif look or the near-black+neon-accent
look that many templates default to — this is a data tool, not a
marketing page, so the palette stays desaturated and the accent is
functional (it *is* the confidence indicator) rather than decorative.

**Type**: Space Grotesk (display/headings, used sparingly — page titles and
card titles only), IBM Plex Sans (body), IBM Plex Mono (anything that is
literally model output: labels, confidence scores, request IDs, model
names). The mono treatment for model output is deliberate: tokens are
discrete units, so the typeface says so.

**Radius**: `0.4rem` — tight enough to read as precise/technical, not the
bubbly `1rem+` common in consumer SaaS.

## Signature element

The **confidence chip** (`src/components/playground/ConfidenceChip.tsx` +
`.confidence-chip` in `index.css`): a monospace label pill whose *own*
bottom edge is a proportional fill in the primary color representing the
model's confidence score — not a separate progress bar next to the label,
the label chip *is* the bar. Reused everywhere a prediction result appears
(playground result, history list) so it reads as the platform's signature
rather than a one-off.

## Motion

Framer Motion is used in exactly three places: the route-change fade/slide
in `AppShell`, the sliding active-nav-item pill in `Sidebar` (`layoutId`
shared-layout animation), and the result-card entrance in the playground.
Nothing else animates — `prefers-reduced-motion` is respected globally via
a CSS media query that collapses all transition/animation durations.

## Layout

Standard enterprise shell: fixed sidebar (collapsible) + top bar (breadcrumbs,
global search, status, notifications, theme, user) + scrollable content area.
Not reinvented — for a data-dense internal tool, the value is in the content
(the confidence chip, the explicit "coming soon" states, the live status
indicator), not in a novel navigation paradigm.
