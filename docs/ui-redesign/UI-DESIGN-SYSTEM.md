# Infinite Canvas — UI Design System Specification (v1.0)

**Document Version:** 1.0.0 (Phase 1 Baseline)
**Target Environment:** Vanilla HTML / CSS / JavaScript (FastAPI Backend)
**Namespace Standard:** All design tokens and new utility components must use the `--ui-*` and `.ui-*` prefix.

---

## 1. Design Principles

Inspired by Lovart's quiet, content-first, AI-native interface, but tailored for Infinite Canvas's technical canvas capabilities:

1. **Content-First, Canvas-First:** The creative work (images, workflows, prompt blocks) is the primary content. UI chrome (HUD, panels, toolbars) must remain quiet, translucent, and unobtrusive.
2. **Neutral & Calm Palette:** Avoid hyper-saturated accents, gratuitous neon gradients, and heavy glassmorphism. Use warm-neutral off-whites in light mode and neutral charcoal grays in dark mode.
3. **Border Over Shadow:** Rely on crisp, subtle 1px borders rather than heavy, blurry drop shadows to define spatial boundaries.
4. **Deliberate Typography:** Limit font-weight to 400 (normal), 500 (medium), and 600 (semibold). Eliminate visual clutter caused by widespread 800/850/900 bold declarations.
5. **Spatial Predictability:** Use an 8-point / 4-point spacing grid (`4px`, `8px`, `12px`, `16px`, `20px`, `24px`, `32px`).
6. **Additive & Non-Destructive:** During redesign phases, always use additive overrides that preserve underlying DOM structures, coordinates, and JavaScript interaction contracts.

---

## 2. Color Tokens

All color tokens are scoped under `--ui-*`.

### 2.1 Surfaces & Canvas

| Token Name | Light Value | Dark Value | Intended Usage |
|---|---|---|---|
| `--ui-bg-canvas` | `#F5F5F4` | `#121212` | Main viewport background behind world |
| `--ui-bg-canvas-grid` | `rgba(0, 0, 0, .06)` | `rgba(255, 255, 255, .05)` | Infinite canvas radial dot grid |
| `--ui-bg-surface` | `#FFFFFF` | `#1A1A1A` | Solid cards, inputs, drop-down bodies |
| `--ui-bg-surface-raised` | `#FFFFFF` | `#222222` | Cards inside containers, hover card items |
| `--ui-bg-surface-overlay` | `rgba(255, 255, 255, .92)` | `rgba(26, 26, 26, .92)` | Floating HUD, panels, modals with blur |
| `--ui-bg-hover` | `rgba(0, 0, 0, .035)` | `rgba(255, 255, 255, .05)` | Hover state on ghost buttons & list items |
| `--ui-bg-active` | `rgba(0, 0, 0, .06)` | `rgba(255, 255, 255, .08)` | Pressed or active state on controls |
| `--ui-bg-soft` | `#F5F5F4` | `#161616` | Inset backgrounds, input defaults |
| `--ui-bg-muted` | `#EDEDEC` | `#222222` | Disabled inputs, pill tracks |

### 2.2 Text Hierarchy

| Token Name | Light Value | Dark Value | Intended Usage |
|---|---|---|---|
| `--ui-text-primary` | `#1C1C1A` | `#E8E8E6` | Primary headings, titles, active text |
| `--ui-text-secondary` | `#6B6B68` | `#9E9E9A` | Secondary labels, descriptions, subtitles |
| `--ui-text-tertiary` | `#9C9C98` | `#6E6E6A` | Timestamps, metadata, hints |
| `--ui-text-placeholder` | `#B5B5B2` | `#545452` | Empty input hints, empty states |
| `--ui-text-inverse` | `#FFFFFF` | `#1C1C1A` | Text on inverted or accent elements |
| `--ui-text-on-accent` | `#FFFFFF` | `#1C1C1A` | High-contrast text on primary active buttons |

### 2.3 Borders

| Token Name | Light Value | Dark Value | Intended Usage |
|---|---|---|---|
| `--ui-border-subtle` | `rgba(0, 0, 0, .06)` | `rgba(255, 255, 255, .06)` | Dividers, internal row separators |
| `--ui-border-default` | `rgba(0, 0, 0, .10)` | `rgba(255, 255, 255, .10)` | Standard card, input, and panel borders |
| `--ui-border-strong` | `rgba(0, 0, 0, .18)` | `rgba(255, 255, 255, .18)` | Hovered cards, selected states |
| `--ui-border-focus` | `#1C1C1A` | `#E8E8E6` | Focused inputs, primary rings |

### 2.4 Accent & Semantics

| Token Name | Light Value | Dark Value | Usage |
|---|---|---|---|
| `--ui-accent` | `#1C1C1A` | `#E8E8E6` | Primary buttons, active toggle chips |
| `--ui-accent-hover` | `#2E2E2B` | `#D4D4D2` | Accent hover state |
| `--ui-accent-soft` | `rgba(28, 28, 26, .08)` | `rgba(232, 232, 230, .08)` | Active pill backgrounds, subtle tags |
| `--ui-danger` | `#DC2626` | `#F87171` | Delete, destructive actions, error states |
| `--ui-success` | `#16A34A` | `#4ADE80` | Saved states, completions |
| `--ui-warning` | `#CA8A04` | `#FACC15` | Caution alerts, warnings |

---

## 3. Typography

All typography relies on the bundled `Inter` font family without external CDNs:

```css
--ui-font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
--ui-font-mono: 'JetBrains Mono', 'SF Mono', monospace;
```

### Type Ramp
- `--ui-text-xs`: `11px` (metadata, badges, small hints)
- `--ui-text-sm`: `12px` (HUD buttons, navigation labels, tags)
- `--ui-text-md`: `13px` (body text, input text, dropdown items)
- `--ui-text-lg`: `15px` (panel section titles, modal subheads)
- `--ui-text-xl`: `18px` (page titles, prominent modal titles)

### Font Weights
- `--ui-weight-normal`: `400` (body copy, prompt text)
- `--ui-weight-medium`: `500` (labels, buttons, HUD controls)
- `--ui-weight-semibold`: `600` (card titles, primary action headings)

---

## 4. Spacing Scale

```css
--ui-space-1:   4px;
--ui-space-2:   8px;
--ui-space-3:   12px;
--ui-space-4:   16px;
--ui-space-5:   20px;
--ui-space-6:   24px;
--ui-space-8:   32px;
--ui-space-10:  40px;
--ui-space-12:  48px;
```

---

## 5. Border Radius

```css
--ui-radius-xs:   6px;   /* Small badges, internal button tags */
--ui-radius-sm:   8px;   /* Standard buttons, dropdown items, selects */
--ui-radius-md:   10px;  /* Floating HUD buttons, form inputs */
--ui-radius-lg:   12px;  /* Canvas cards, minimap */
--ui-radius-xl:   16px;  /* Modals, slide-out panels, composer card */
--ui-radius-pill: 999px; /* Status pills, circular toggles */
```

---

## 6. Shadow System

```css
--ui-shadow-xs:       0 1px 2px rgba(0, 0, 0, .04);
--ui-shadow-sm:       0 2px 6px rgba(0, 0, 0, .05), 0 1px 2px rgba(0, 0, 0, .03);
--ui-shadow-md:       0 4px 12px rgba(0, 0, 0, .06), 0 1px 3px rgba(0, 0, 0, .04);
--ui-shadow-floating: 0 8px 24px rgba(0, 0, 0, .08), 0 2px 6px rgba(0, 0, 0, .04);
```

In Dark Mode, shadow opacities increase to account for lower ambient contrast against dark surfaces.

---

## 7. Motion

Interaction transitions must remain fast and discrete (120ms–160ms). Transitioning layout or transform properties on nodes during canvas pan/zoom is strictly prohibited.

```css
--ui-duration-fast:    120ms;
--ui-duration-normal:  160ms;
--ui-duration-slow:    240ms;

--ui-ease-standard:    cubic-bezier(.4, 0, .2, 1);
```

---

## 8. Z-Index Layer Standards

Reference hierarchy across Infinite Canvas:
- `0`: Virtual world stage (`.connection-layer`)
- `2`: Base canvas nodes (`.image-node`)
- `10`: Selected canvas node (`.image-node.selected`)
- `12`: Dragged canvas node (`.image-node.dragging`)
- `18`: Selection box marquee (`#selectionBox`)
- `20`: Floating back button (`.smart-back`)
- `30`: World composer card (`#composer`)
- `50`: Context popovers (`.smart-popover`)
- `55`: Slide-out drawers (`#assetPanel`)
- `56`: Top HUD header buttons (`.smart-*-toggle`, `.asset-toggle`)
- `57`: Workflow transfer & shortcut modals
- `60`: System toast (`#toast`)
- `75`: Node creation radial menu (`#createMenu`)
- `85`: Preset management popover (`#promptPresetPanel`)
- `90`: Full-screen dialog backdrop (`.asset-dialog-backdrop`)
- `92`: Image editor modal (`#imageEditModal`)
- `120`: Hover preview lightbox (`#mentionPreview`)

---

## 9. Light Theme Specification
- Background: Warm off-white `#F5F5F4` with 6% opacity black radial dot grid at 24px pitch.
- HUD Chrome: Translucent white `rgba(255, 255, 255, .92)` with 20px blur and subtle 10% black borders.
- Text: Charcoal `#1C1C1A` for primary labels, soft gray `#6B6B68` for secondary text.

---

## 10. Dark Theme Specification
- Background: Deep neutral dark `#121212` with 5% opacity white radial dot grid.
- HUD Chrome: Translucent charcoal `rgba(26, 26, 26, .92)` with 20px blur and 10% white borders.
- Text: Off-white `#E8E8E6` for primary labels, muted gray `#9E9E9A` for secondary text.

---

## 11. Component Conventions

New shared components must use `.ui-*` classes:
- `.ui-button`: Standard button with 8px radius and 160ms transition.
- `.ui-button-primary`: Solid accent button.
- `.ui-button-ghost`: Transparent button with hover background.
- `.ui-input`: Input with subtle border, 10px radius, and `--ui-focus-ring`.
- `.ui-panel`: Surface with 16px radius, border, and blur.

---

## 12. Selector Conventions
- Never use bare tag selectors (`button {}`, `input {}`, `div {}`).
- Always scope overrides to component class or parent container (`.shell .smart-back`, `.composer-card .prompt-input`).
- Maintain existing `data-*` attributes for all JavaScript event delegations.

---

## 13. Future Migration Rules
- **Phase 2 (Workspace Shell):** Migrate `canvas-list.css` using `--ui-*` tokens.
- **Phase 3 (HUD & Chrome):** Refine floating headers, minimap, and context menus.
- **Phase 4 (Canvas Nodes):** Update node visual containers and selection rings.
- **Phase 5 (Composer & Modals):** Modernize prompt composer and image editor without altering logic.
- **Phase 6 (Secondary Pages):** Migrate `asset-manager.css` and `api-settings.css`.
