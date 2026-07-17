# Review Intelligence UI Reference

These mockups translate the approved analysis information architecture into a
desktop and narrow-screen visual system:

- `review-intelligence-report-desktop.png`
- `review-intelligence-report-mobile.png`

They are layout and styling references. Live source, metric, theme, and history
values remain data-driven; sample values or retailer marks invented by the
mockups are not product requirements.

## Design tokens

- Background: true white `#ffffff`
- Sidebar: deep navy `#102437` on desktop; collapsible in Streamlit's native
  mobile sidebar treatment
- Main text: navy `#0f2450`
- Muted text: slate `#64748b`
- Border: `#dbe4f0`
- Primary action: royal blue `#2563eb`, hover `#1d4ed8`
- Positive: `#15803d` on `#f0fdf4`
- Neutral: `#a16207` on `#fffbeb`
- Negative: `#b91c1c` on `#fef2f2`
- Mixed/action: `#4f46e5` on `#eef2ff`
- Radius scale: 10px controls, 14px cards, 18px major surfaces
- Spacing scale: 4, 8, 12, 16, 24, 32, 48px
- Shadow: subtle cool shadow only on major report surfaces

## Typography

- Use Streamlit's system sans-serif stack.
- Page title: 34–42px, 750 weight, tight tracking.
- Section heading: 22–28px, 700–750 weight.
- Card value: 28–34px, 750 weight.
- Body: 15–16px with 1.55–1.7 line height.
- Labels and controls: 13–15px, 600–700 weight where emphasis is needed.

## Component inventory

- URL workspace with one labeled input and primary/secondary actions
- Three-step process strip
- Source/report header with one semantic sentiment badge
- Four metric cards
- Executive summary surface
- Two chart surfaces
- Recurring theme card grid
- Strengths, Concerns, and Recommended actions panels
- Collapsed supporting-evidence disclosure
- Desktop history sidebar using native mobile collapse behavior

## Allowed opening copy

- `Review Intelligence`
- `Extract normalized public reviews, inspect the evidence, then analyze customer signals with Groq.`
- `Review page URL`
- `Extract reviews`
- `Use bundled demo data`
- `How it works`
- `Extract`
- `Review evidence`
- `Analyze`

No credential field, provider selector, retailer branding, marketing
navigation, decorative pretitle, or additional opening metric is allowed.

## Responsive rules

- At desktop widths, actions share a row, metrics form four columns, charts
  form two columns, and insight panels form three columns.
- Below roughly 900px, actions and charts stack and metrics form two columns.
- Below roughly 640px, all major grids become one column except the compact
  two-column metric grid when content remains readable.
- No horizontal scrolling is permitted in the main workspace. Review evidence
  may use Streamlit's table scrolling inside its own bounded surface.

