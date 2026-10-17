# DESIGN.md — PayLens Design System & Visual Tokens

**Framework:** Impeccable Design System Standard  
**Theme:** Linear / Stripe Dark FinTech Grade  
**Target:** `paylens-amd/app.py`  
**Conformance:** WCAG 2.1 AA Compliant  

---

## 1. Design Tokens (`:root`)

```css
:root {
    /* Backgrounds & Elevations */
    --bg-app: #090D16;                  /* Base application background (Obsidian) */
    --bg-sidebar: #0B1120;              /* Elevated navigation sidebar */
    --surface-card: #111827;            /* Surface card panel */
    --surface-hover: #162032;           /* Interactive card hover */
    --surface-selected: #151F33;        /* Selected queue item */
    --surface-formula: rgba(15, 23, 42, 0.95); /* Monospace math formula background */

    /* Borders & Outlines */
    --border-subtle: rgba(255, 255, 255, 0.08); /* Card and panel borders */
    --border-divider: rgba(255, 255, 255, 0.07);/* Structural separators */
    --border-hover: rgba(99, 102, 241, 0.45);   /* Interactive hover glow */

    /* Typography & Contrast */
    --text-primary: #F8FAFC;            /* Primary titles and critical values (>14:1 contrast) */
    --text-secondary: #E2E8F0;          /* Explanations and readable body (>10:1 contrast) */
    --text-muted: #94A3B8;              /* Subtitles, labels, and metadata (>5.5:1 contrast, WCAG AA) */

    /* Brand Accents */
    --accent-indigo: #6366F1;           /* Primary interaction accent */
    --accent-indigo-light: #818CF8;     /* Badge border and glow */
    --accent-cyan: #38BDF8;             /* Technical metrics and telemetry */

    /* Semantic Status Rails */
    --status-leak: #EF4444;             /* Capital at risk value */
    --status-leak-text: #FCA5A5;        /* Leakage badge text */
    --status-leak-bg: rgba(239, 68, 68, 0.18);
    --status-leak-border: rgba(239, 68, 68, 0.35);

    --status-recovery: #F59E0B;         /* Recovery / Abandoned checkout */
    --status-recovery-text: #FDE68A;
    --status-recovery-bg: rgba(245, 158, 11, 0.18);
    --status-recovery-border: rgba(245, 158, 11, 0.35);

    --status-stockout: #A78BFA;         /* Inventory margin risk */
    --status-stockout-text: #DDD6FE;
    --status-stockout-bg: rgba(139, 92, 246, 0.18);
    --status-stockout-border: rgba(139, 92, 246, 0.35);

    --status-success: #10B981;          /* Approved recovery / Grounding passed */
    --status-success-text: #6EE7B7;
    --status-success-bg: rgba(16, 185, 129, 0.15);
    --status-success-border: rgba(16, 185, 129, 0.35);

    /* Font Families */
    --font-sans: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    --font-mono: 'JetBrains Mono', monospace;

    /* Modular Type Scale */
    --text-xs: 0.70rem;                 /* Badges, micro labels, counter tags */
    --text-sm: 0.76rem;                 /* Sidebar headers, captions, subtext */
    --text-base: 0.86rem;               /* Queue titles, explanation body, tabs */
    --text-md: 0.95rem;                 /* Card values, interactive buttons */
    --text-lg: 1.25rem;                 /* Section titles, inspector entity header */
    --text-xl: 1.65rem;                 /* Hero KPI metrics, inspector hero amount */

    /* Typographic Rhythm & Leading */
    --leading-none: 1.0;                /* Badges, tags, tight status chips */
    --leading-tight: 1.25;              /* Headers, metric cards, titles */
    --leading-normal: 1.5;              /* UI text, queue rows, tabs */
    --leading-relaxed: 1.65;            /* Long-form explanations, audit reports */

    /* Letter Spacing & Tracking */
    --tracking-tight: -0.025em;         /* Display numbers and large headings */
    --tracking-normal: 0em;             /* Prose and explanations */
    --tracking-wide: 0.05em;            /* Tab titles, code snippets */
    --tracking-wider: 0.08em;           /* Uppercase category labels, badges */
}
```

---

## 2. Typographic Hierarchy & Reading Ergonomics

| Element | Font Family | Size Token | Weight | Leading | Tracking | Tabular Nums |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **Brand Wordmark** | Sans | `var(--text-xl)` | 800 | `var(--leading-tight)` | `var(--tracking-tight)` | No |
| **KPI Metric Value** | Mono | `var(--text-xl)` | 700 | `var(--leading-tight)` | `var(--tracking-tight)` | **Yes** |
| **Inspector Amount** | Mono | `var(--text-xl)` | 700 | `var(--leading-tight)` | `var(--tracking-tight)` | **Yes** |
| **Inspector Header** | Sans | `var(--text-lg)` | 700 | `var(--leading-tight)` | `var(--tracking-tight)` | No |
| **Queue Impact Value**| Mono | `var(--text-md)` | 700 | `var(--leading-tight)` | `var(--tracking-tight)` | **Yes** |
| **Explanation Prose** | Sans | `var(--text-base)`| 400 | `var(--leading-relaxed)`| `var(--tracking-normal)`| No (Max 72ch) |
| **Math Formula** | Mono | `var(--text-base)`| 500 | `var(--leading-normal)` | `var(--tracking-wide)` | **Yes** |
| **Queue Item Title** | Sans | `var(--text-base)`| 600 | `var(--leading-normal)` | `var(--tracking-normal)`| No |
| **Status Badge** | Sans | `var(--text-xs)` | 700 | `var(--leading-none)` | `var(--tracking-wide)` | No |
| **Category Label** | Sans | `var(--text-sm)` | 700 | `var(--leading-tight)` | `var(--tracking-wider)`| No (Uppercase) |
| **Footnote / Notice** | Sans | `var(--text-sm)` | 500 | `var(--leading-normal)` | `var(--tracking-wide)` | No |

### Reading Measure (Line Length)
- **Long-form explanation text (`.explanation-box`):** Capped at `max-width: 72ch` to adhere to typographic standards (60–75 characters per line), eliminating eye travel fatigue across wide displays.
- **Tabular Numerics:** Enforced via `font-feature-settings: "tnum" 1, "zero" 1; font-variant-numeric: tabular-nums` on all currency, metrics, and data tables to preserve vertical decimal alignment.

---

## 3. Interactive Component Standards

* **Queue Item Card (`.queue-item`):**
  * Border radius: `10px`
  * Padding: `14px 16px`
  * Active Selection: `1px solid var(--accent-indigo)` + `box-shadow: 0 0 15px rgba(99, 102, 241, 0.2)`
  * Hover Transition: `all 0.15s ease`
* **Deal Badge (`.deal-badge`):**
  * Border radius: `6px`
  * Padding: `3px 8px`
  * Letter-spacing: `0.05em` uppercase
* **Sanitization Protocol:**
  * All user, merchant, and order string interpolations are processed through `esc()` (`html.escape`) before DOM insertion.

---

## 4. Distilled Layout Architecture

* **Hero KPI Grid:**
  * 3 dynamic operational columns (`Capital at Risk`, `Approved & Recovered Today`, `Detector Accuracy & Grounding`).
  * Left-border status accent (`3px solid var(--status-...)`) for instant visual distinction without container clutter.
* **Goal Optimization Header:**
  * Inline live weights directly bound to the section header, eliminating detached auxiliary pill rows.
* **Uninterrupted Inspector Runway:**
  * Single-tier inspector header with a bottom divider, removing redundant nested card containers.
  * Direct flow: Evidence Chart -> Model Explanation -> Tone Selector -> Action Draft -> Dispatch Trigger.
  * Diagnostic and audit testing tools docked cleanly at the bottom in collapsible trace expanders.
