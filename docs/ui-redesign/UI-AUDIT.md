# UI Architecture Audit — Infinite Canvas

**Audit Date:** 2026-09-03
**Branch:** `feature/ui-lovart-redesign-v1`
**Auditor Role:** Senior UI Engineer + Product Designer
**Reference Product:** [Lovart.ai](https://www.lovart.ai)
**Status:** ✅ Read-only audit — no product code modified

---

## Table of Contents

1. [Current UI Architecture](#1-current-ui-architecture)
2. [Page Structure](#2-page-structure)
3. [Smart Canvas DOM Structure](#3-smart-canvas-dom-structure)
4. [CSS Architecture](#4-css-architecture)
5. [JS DOM Selector Dependencies](#5-js-dom-selector-dependencies)
6. [Critical DOM IDs / Classes — DO NOT Rename](#6-critical-dom-ids--classes--do-not-rename)
7. [Top 10 UI Problems](#7-top-10-ui-problems)
8. [Lovart Design Principles to Adopt](#8-lovart-design-principles-to-adopt)
9. [Recommended New UI Information Architecture](#9-recommended-new-ui-information-architecture)
10. [UI Redesign Risk Points](#10-ui-redesign-risk-points)
11. [Recommended Implementation Phases](#11-recommended-implementation-phases)
12. [Per-Phase File Change Estimates](#12-per-phase-file-change-estimates)

---

## 1. Current UI Architecture

### 1.1 Technology Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (single `main.py`, 20,547 lines, ~953 KB) |
| Static Serving | Starlette `StaticFiles` mount at `/static/`, `/output/`, `/assets/` |
| Frontend | Vanilla HTML + CSS + JavaScript (no framework) |
| Icons | Lucide.js (via CDN) |
| CSS Utility | Tailwind CSS (CDN runtime) — used sparingly alongside custom CSS |
| Theme | Custom CSS variables + `theme.js` + `theme.css` |
| i18n | Custom `i18n.js` with `data-i18n` attributes |
| Real-time | Single WebSocket endpoint (`/ws/stats`) |
| Canvas Rendering | DOM-based (not `<canvas>` 2D/WebGL) — nodes are `<div>` elements |

### 1.2 Application Shell Architecture

```
index.html (SPA Shell)
├── <aside#studioSidebar> — 80px collapsed / 220px expanded sidebar
│   ├── Logo toggle (pin/unpin)
│   ├── Nav items (zimage, enhance, klein, angle, online, gpt-chat, canvas, asset-manager)
│   └── Side actions (api-settings, theme, language, comfyui-settings, github, update)
└── <main.stage> — iframe viewport (border-radius: 32px, margin: 16px)
    ├── iframe#frame-zimage → /static/zimage.html
    ├── iframe#frame-enhance → /static/enhance.html
    ├── iframe#frame-klein → /static/klein.html
    ├── iframe#frame-angle → /static/angle.html
    ├── iframe#frame-online → /static/online.html
    ├── iframe#frame-gpt-chat → /static/gpt-chat.html
    ├── iframe#frame-asset-manager → /static/asset-manager.html
    ├── iframe#frame-api-settings → /static/api-settings.html
    ├── iframe#frame-comfyui-settings → /static/comfyui-settings.html
    └── iframe#frame-canvas → /static/canvas-list.html
```

> [!IMPORTANT]
> The app uses an **iframe-per-page** architecture. Each page (`zimage`, `enhance`, etc.) runs in its own iframe within the `index.html` shell. Theme, language, and scale are synced via `postMessage` and `BroadcastChannel('studio-api')`.

### 1.3 Smart Canvas Entry Flow

```
index.html → switchUI(this, 'canvas') → activates iframe#frame-canvas
  → canvas-list.html (Project workspace with pannable board)
    → User clicks a canvas card
      → openCanvas(c) → navigates parent to /static/smart-canvas.html?id=xxx&project=yyy
        (exits iframe architecture, becomes full-page)
```

### 1.4 Backend Architecture (UI-Relevant)

- **Single Route for HTML:** Only `GET /` → `index.html`. All other pages served via `/static/` mount.
- **Canvas Persistence:** `PUT /api/canvases/{id}` with optimistic locking via `base_updated_at` (HTTP 409 on conflict).
- **Real-time Sync:** WebSocket broadcasts `canvas_updated`, `asset_library_updated`, `new_image` events.
- **Media Thumbnails:** `/api/media-preview?url=...&w=512` for lazy-loaded downscaled previews.
- **Version Stamping:** `sync_static_html_versions()` at startup appends `?v=<version>.<mtime>` to all static references.

---

## 2. Page Structure

### 2.1 Page Inventory

| Page | HTML | CSS | JS | Size (JS) | Purpose |
|---|---|---|---|---|---|
| Shell | `index.html` (122 KB) | Inline | Inline | ~30 KB | App shell, sidebar, iframe router |
| Canvas List | `canvas-list.html` (5.6 KB) | `canvas-list.css` (27 KB) | `canvas-list.js` (48 KB) | 48 KB | Project workspace, pannable board |
| Smart Canvas | `smart-canvas.html` (41 KB) | `smart-canvas.css` (208 KB) | `smart-canvas.js` (988 KB) | **988 KB** | Infinite canvas editor |
| Asset Manager | `asset-manager.html` (2.8 KB) | `asset-manager.css` (51 KB) | `asset-manager.js` (267 KB) | 267 KB | Media/prompt/workflow library |
| API Settings | `api-settings.html` (47 KB) | `api-settings.css` (202 KB) | `api-settings.js` (212 KB) | 212 KB | Provider/key/model config |
| Classic Canvas | `canvas.html` (33 KB) | `canvas.css` (165 KB) | `canvas.js` (786 KB) | 786 KB | Legacy ComfyUI canvas |
| Others | `zimage`, `enhance`, `klein`, `angle`, `online`, `gpt-chat` | Various | Various | — | Single-purpose generation UIs |

> [!WARNING]
> `smart-canvas.js` is **988 KB** — a massive single file. Any refactoring must be incremental and non-breaking.

### 2.2 Inter-Page Communication

| Channel | From → To | Events |
|---|---|---|
| `postMessage` | `index.html` → child iframes | `studio-theme`, `studio-lang`, `studio-ui-scale`, `studio-ui-scale-pause`, `canvas-focus` |
| `postMessage` | `index.html` (WS) → iframes | `canvas_updated`, `asset_library_updated` |
| `BroadcastChannel('studio-api')` | Any tab ↔ Any tab | `providers-changed`, `workflows-changed`, `comfy-instances-changed`, theme/lang sync |

---

## 3. Smart Canvas DOM Structure

### 3.1 Major DOM Hierarchy

```
#shell.shell — 100vw×100vh viewport, grab cursor, dot-grid background
├── #world.world — 6000×4000px virtual world, transform: translate(X,Y) scale(S)
│   ├── #composer.composer — Floating AI prompt card (z-index: 30)
│   │   └── .composer-card
│   │       ├── .composer-head → #engineSelect, #apiKindToggle
│   │       ├── #inputThumbsRow — Reference image thumbnails
│   │       ├── #inputPromptPreview — Upstream text inheritance
│   │       ├── .prompt-row → #promptInput[contenteditable], #mentionPicker
│   │       ├── .param-row → #dynamicParams — Engine-specific controls
│   │       └── .composer-actions → #cascadeRunBtn, #runBtn
│   ├── svg.connection-layer — Bezier connection lines (z-index: 0)
│   └── [Dynamic .image-node elements] — Canvas nodes
│       ├── .node-port.port-in / .port-out — Connection ports
│       ├── .image-wrap — Media display area
│       ├── .node-resize-handle — SE corner resize
│       └── .floating-node-actions — Per-node toolbar
│
├── Floating HUD Layer (position: fixed, scaled via CSS zoom)
│   ├── .smart-back — Return to canvas list (z-index: 20)
│   ├── #smartTitle — Canvas title label (z-index: 10)
│   ├── #createMenu — Node creation menu (z-index: 75)
│   ├── #minimap — Radar minimap (z-index: 8)
│   ├── #smartArrangeBtn — Auto-arrange button (z-index: 9)
│   ├── Header toggles: #smartWorkflowToggle, #smartShortcutToggle, #smartLogToggle, #assetToggle
│
├── Slide-out Panels
│   ├── #assetPanel — Right sidebar asset library (z-index: 55)
│   ├── #promptPresetPanel — Prompt presets (z-index: 85)
│   ├── #promptTemplatePanel — Template library (z-index: 57)
│   ├── #smartWorkflowTransferModal — Import/export (z-index: 57)
│
├── Modals
│   ├── #imageEditModal — Full-screen editor (z-index: 92)
│   ├── #smartLogModal — Generation logs (z-index: 86)
│   ├── #smartShortcutModal — Shortcuts (z-index: 57)
│   ├── #assetDialogBackdrop — Folder naming (z-index: 90)
│
└── Overlays
    ├── #selectionBox — Rubber-band marquee (z-index: 18)
    ├── #toast — Notification toast (z-index: 60)
    └── #mentionPreview — Image hover preview (z-index: 120)
```

### 3.2 Node Types

| Type | Class | Description |
|---|---|---|
| Image Node | `.image-node` | Media container (images/videos), draggable, resizable, connectable |
| Prompt Node | `.image-node.prompt-smart-node` | Text prompt with @mention tokens, LLM expansion |
| Loop Node | `.image-node.loop-smart-node` | Batch automation with variable prompts |
| MiniMax Node | `.image-node.minimax-smart-node` | Multi-track video timeline editor |
| Group Node | `.image-node.smart-group-node` | Container grouping multiple child nodes |
| Group Member | `.image-node.smart-group-member-node` | Child of a group node |

### 3.3 Node State Classes

| Class | State |
|---|---|
| `.selected` | User-selected (blue highlight ring) |
| `.dragging` | Being dragged (elevated z-index) |
| `.node-running` | Generation in progress (spinner) |
| `.node-pending` | Queued for generation |
| `.empty-node` | No images yet |
| `.auto-group-armed` | Hovering over another node for auto-grouping |

---

## 4. CSS Architecture

### 4.1 Design Token System

Each page defines its own `:root` and `.theme-dark` variables. Tokens are **not globally unified** — they are redeclared per CSS file.

**Core Tokens (consistent across files):**

| Token | Light | Dark |
|---|---|---|
| `--page` | `#f8fafc` | `#0f141d` |
| `--panel` | `rgba(255,255,255,.9)` | `rgba(23,29,41,.92)` |
| `--card` | `#fff` | `#171d29` |
| `--text` | `#111827` | `#e5e9f0` |
| `--muted` | `#64748b` | `#8f9aab` |
| `--faint` | `#94a3b8` | `#657286` |
| `--line` | `#e8edf3` | `#2a3444` |
| `--soft` | `#f8fafc` | `#111722` |
| `--strong` | `#111827` | `#d8dee9` |
| `--shadow` | `rgba(15,23,42,.08)` | `rgba(0,0,0,.28)` |

**Component-Specific Runtime Tokens:**
- `--prompt-h` — Dynamic height for prompt input (60px–380px)
- `--compare-pos` — Split-screen comparison slider position (default 50%)
- `--ctrl-font`, `--ctrl-icon`, `--ctrl-height` — Compact parameter control sizing
- `--studio-ui-scale` — Global UI zoom factor

### 4.2 Z-Index Layer Map (Smart Canvas)

| Layer | Z-Index | Elements |
|---|---|---|
| Background | 0 | Connection SVG, group backdrop |
| Nodes | 2 | `.image-node` base level |
| Selected | 10 | `.image-node.selected` |
| Dragging | 12 | `.image-node.dragging` |
| Selection Box | 18 | `#selectionBox`, floating menus |
| Back Button | 20 | `.smart-back` |
| Composer | 30 | `#composer` |
| Popovers | 40–50 | Loop controls, parameter menus |
| Asset Panel | 55 | `#assetPanel` |
| Header Buttons | 56 | Toggle buttons |
| Template/Workflow | 57 | Slide-out modals |
| Toast | 60 | `#toast` |
| Mention Picker | 70 | `#mentionPicker` |
| Create Menu | 75 | `#createMenu` |
| Preset Panel | 85 | `#promptPresetPanel` |
| Log Modal | 86 | `#smartLogModal` |
| Asset Preview | 88 | `#assetHoverPreview` |
| Folder Dialog | 90 | `#assetDialogBackdrop` |
| Image Editor | 92 | `#imageEditModal` |
| Mention Preview | 120 | `#mentionPreview` |

### 4.3 Responsive Breakpoints

| Breakpoint | Smart Canvas | Canvas List | Asset Manager |
|---|---|---|---|
| `≤900px` | Header toggles collapse to icon-only | — | — |
| `≤760px` | Composer width adapts, minimap shrinks | Sidebar collapses, cards shrink | — |
| `≤1280px` | — | — | 3-col → 2-col grid, detail panel moves below |
| `≤820px` | — | — | Single column |

### 4.4 Theme Switching Mechanism

1. **FOUC Prevention:** Inline `<script>` in `<head>` reads `localStorage('studio_theme')` and applies `.theme-dark` / `.studio-theme-dark` before any render.
2. **Runtime Toggle:** `toggleTheme()` in `theme.js` toggles classes, dispatches `studio-theme-change` CustomEvent, broadcasts via `BroadcastChannel`.
3. **Cross-iframe Sync:** Parent posts `{ type: 'studio-theme', theme }` to all child iframes.

---

## 5. JS DOM Selector Dependencies

### 5.1 Smart Canvas (`smart-canvas.js`) — 988 KB

**getElementById References (115+ unique IDs):**

| Category | IDs |
|---|---|
| Core viewport | `shell`, `world`, `composer`, `smartTitle`, `selectionBox` |
| Minimap | `minimap`, `minimapContent`, `minimapViewport` |
| Composer | `engineSelect`, `apiKindToggle`, `inputThumbsRow`, `inputPromptPreview`, `promptInput`, `composerTemplateBtn`, `mentionPicker`, `promptResize`, `dynamicParams`, `runBtn`, `cascadeRunBtn`, `fileInput` |
| Presets | `promptPresetPanel`, `promptPresetClose`, `promptPresetStatus`, `promptPresetSelect`, `promptPresetName`, `promptPresetText`, `promptPresetApply`, `promptPresetDelete`, `promptPresetNew`, `promptPresetSave` |
| Templates | `promptTemplatePanel`, `promptTemplateClose`, `promptTemplateSearch`, `promptTemplateLibrarySelect`, `promptTemplateCats`, `promptTemplateBody` |
| Workflow | `smartWorkflowToggle`, `smartWorkflowTransferModal`, `smartWorkflowTransferSub`, `smartWorkflowExportMeta`, `smartWorkflowImportInput`, `smartWorkflowImportDropZone` |
| Asset panel | `assetToggle`, `assetPanel`, `assetCloseBtn`, `assetLibrarySelect`, `assetCategorySelect`, `assetGrid`, `assetDropZone`, `workflowEmpty`, `assetImageControls`, `assetAddCategoryBtn`, `assetRenameCategoryBtn`, `assetDialogBackdrop`, `assetDialogTitle`, `assetDialogInput`, `assetDialogCancel`, `assetDialogOk`, `assetHoverPreview` |
| Modals | `smartShortcutToggle`, `smartShortcutModal`, `smartLogToggle`, `smartLogModal`, `smartLogList`, `toast`, `mentionPreview` |
| Image Editor | `imageEditModal`, `imageEditTitle`, `imageEditSub`, `imageCropTools`, `imagePreviewTools`, `previewMetaHint`, `panoramaControls`, `imageMaskTools`, `maskBrushSize`, `imageBrushTools`, `paintBrushColor`, `paintBrushSize`, `imageResizeTools`, `imageGridTools`, `imageEditStage`, `previewStage`, `previewFrame`, `previewCurrentImage`, `previewCurrentVideo`, `panoramaStage`, `panoramaCanvas`, `cropCanvas`, `cropImage`, `gridJoinCanvas`, `editDrawCanvas`, `editTextCanvas`, `cropBox`, `cropHandle`, `outpaintFrame`, `imageEditCancelBtn`, `imageEditApplyBtn`, `imageEditZoomLabel` |

**querySelectorAll Patterns:**
- `world.querySelectorAll('.image-node')` — All canvas nodes
- `world.querySelector('.image-node[data-id="..."]')` — Specific node lookup
- `[data-smart-node-action]`, `[data-smart-group-action]` — Action dispatch
- `[data-param]`, `[data-toggle-param]`, `[data-smart-param]` — Parameter controls
- `[data-comfy-param]`, `[data-comfy-pick]`, `[data-comfy-bool]` — ComfyUI params
- `[data-rh-param]`, `[data-rh-pick]`, `[data-rh-bool]` — RunningHub params
- `[data-crop-ratio]`, `[data-panorama-ratio]`, `[data-brush-tool]` — Editor tools
- `[data-asset-tab]`, `[data-create-type]` — Tab/menu selections
- `svg.connection-layer`, `path[data-connection-key]` — Connection lines
- `.node-port.port-in`, `.node-port.port-out` — Connection ports

### 5.2 Canvas List (`canvas-list.js`) — 48 KB

**getElementById:** `board`, `boardWorld`, `boardEmptyHint`, `boardProjectName`, `boardCanvasCount`, `projectList`, `trashEntry`, `trashBadge`, `trashPanel`, `trashList`, `trashClose`, `newProjectBtn`, `newProjectRow`, `newProjectInput`, `newProjectConfirm`, `newProjectCancel`, `newCanvasBtn`, `boardRefresh`, `boardResetView`, `pasteCanvasBtn`, `emptyCreateCanvasBtn`, `boardStatus`

**Dynamic Class Queries:** `.ws-card`, `.ws-card-pop`, `.ws-create-card`, `.ws-card-menu`, `.ws-card-delete-confirm`, `.ws-project-row`, `.ws-project-name`, `.ws-proj-act`

### 5.3 Asset Manager (`asset-manager.js`) — 267 KB

**Root Mounts:** `assetManagerRoot`, `assetStatus`, `refreshBtn`, `storageSettingsBtn`, `assetUploadInput`

**Dynamic IDs:** `assetSearch`, `workflowSearch`, `promptSearch`, `localUploadSearch`, `canvasAssetSearch`, `canvasAssetSort`, `assetEditName`, `assetMoveTarget`

**Event Delegation via data-attributes:** `data-asset-lib`, `data-asset-cat`, `data-asset-card`, `data-asset-check`, `data-workflow-card`, `data-prompt-row`, `data-localup-card`, `data-canvas-asset-card`, `data-pref-tab`, `data-storage-close`, `data-storage-save`

### 5.4 API Settings (`api-settings.js`) — 212 KB

**78 top-level DOM constants** including: `providerList`, `settingsContent`, `recommendContent`, `nameInput`, `idInput`, `baseInput`, `keyInput`, `protocolInput`, `testUrlBtn`, `imageModelList`, `chatModelList`, `videoModelList`, `modelPickerOverlay`, `pickerFilter`, `pickerList`

---

## 6. Critical DOM IDs / Classes — DO NOT Rename

> [!CAUTION]
> Renaming or removing any of the following elements will break core functionality. Each is referenced by JS coordinate math, drag/resize engines, connection systems, or persistence logic.

### 6.1 Absolute No-Touch Elements (Smart Canvas)

| Element | Why Critical |
|---|---|
| `#shell` | `screenToWorld()`, `viewportCenter()`, `getBoundingClientRect()` — all coordinate math anchors here |
| `#world` | `transform: translate(X,Y) scale(S)` applied directly; all node positions are children of this element |
| `#composer` | Positioned in world coordinates; wrapped in `#world` for proper transform-space alignment |
| `.image-node` | Used by `world.querySelectorAll('.image-node')`, drag engine, resize engine, connection engine |
| `.image-node[data-id="..."]` | Node lookup by ID for save/load/update; persistence depends on this |
| `.node-port.port-in` / `.port-out` | Connection drag start/end target detection via `e.target.closest()` |
| `.node-resize-handle` | Resize engine attaches mousedown handler; matched by class in event delegation |
| `svg.connection-layer` | Connection line rendering target; queried as `svg.connection-layer` |
| `path[data-connection-key]` | Individual connection identification for deletion/update |
| `data-studio-scale="off"` | On `<html>` — prevents `theme.js` from scaling body, which would break pointer math |

### 6.2 Canvas List No-Touch Elements

| Element | Why Critical |
|---|---|
| `#board` | Pan/zoom mouse events bound here; `screenToWorld()` uses its rect |
| `#boardWorld` | `transform: translate(X,Y) scale(S)` applied; cards are children |
| `.ws-card[data-canvas-id="..."]` | Card lookup, drag position persistence |

### 6.3 Cross-Page No-Touch Elements

| Element | Why Critical |
|---|---|
| `#studioSidebar` | Sidebar pin/unpin state machine; expansion animation coordination |
| `.stage` iframe IDs (`frame-zimage`, `frame-canvas`, etc.) | `switchUI()` uses ID pattern `frame-{pageId}` |
| `#assetManagerRoot` | Asset manager JS renders entire view into this single mount point |
| `#providerList` | API settings drag-sort and provider rendering target |

### 6.4 Data Attributes — No Rename

All `data-*` attributes used in event delegation:
- `data-smart-node-action`, `data-smart-group-action`
- `data-param`, `data-toggle-param`, `data-smart-param`
- `data-comfy-param`, `data-comfy-pick`, `data-comfy-bool`, `data-comfy-random`
- `data-rh-param`, `data-rh-pick`, `data-rh-bool`, `data-rh-random`
- `data-crop-ratio`, `data-panorama-ratio`, `data-brush-tool`
- `data-asset-tab`, `data-create-type`, `data-image-edit-mode`
- `data-canvas-id`, `data-id`

---

## 7. Top 10 UI Problems

### Problem 1: No Unified Design Token System
Each CSS file (`smart-canvas.css`, `canvas-list.css`, `asset-manager.css`, `api-settings.css`) redeclares its own `:root` variables. Token names are similar but values drift (e.g., `--page: #f8fafc` vs `--page: #f5f6f8`). There is no single source of truth, making cross-page visual consistency fragile.

### Problem 2: Monolithic JavaScript Files
`smart-canvas.js` is **988 KB** in a single file. `canvas.js` is 786 KB. These files are unmaintainable — finding a specific function requires searching through ~20K lines. No module system, no imports, no component encapsulation.

### Problem 3: Inconsistent Typography Scale
There is no defined type ramp. Font sizes are hardcoded throughout: `13px`, `14px`, `15px`, `11px`, `12px` scattered without a systematic scale. Line heights and letter-spacing are inconsistent between pages.

### Problem 4: Inconsistent Spacing System
Padding, margins, gaps, and border-radii use arbitrary pixel values. No spacing scale (e.g., 4/8/12/16/24/32/48). This creates visual noise — elements don't align to a grid and padding feels random across components.

### Problem 5: Poor Information Density on Canvas
The Smart Canvas composer card and node toolbars take up significant visual space. Controls are dense but not well-organized. Compared to Lovart's clean hierarchy, the current UI feels cluttered with parameters, toggles, and buttons competing for attention.

### Problem 6: Heavy Visual Weight on Controls
Buttons, badges, labels, and status indicators all compete visually. There's no clear hierarchy between primary actions (Run, Create) and secondary actions (Arrange, Workflow Transfer). Everything feels the same weight.

### Problem 7: Z-Index Fragility
The z-index stack spans from 0 to 120 across 20+ layers. There's no named layer system — values are magic numbers assigned ad hoc. Adding new overlays risks clipping or occlusion bugs.

### Problem 8: Modal / Panel Inconsistency
Panels, modals, drawers, and popovers use different animation patterns, backdrop styles, and dismiss behaviors. Some use `.active` class, others use `.open`, some check `hidden` attribute. No consistent overlay system.

### Problem 9: Dark Theme Has Low Contrast in Some Areas
Several dark theme tokens produce insufficient contrast. `--muted: #657286` on `--card: #171d29` is only ~3.2:1 ratio. Status indicators and secondary text can be hard to read.

### Problem 10: Canvas List Cards Lack Visual Polish
Canvas cards (`.ws-card`) are basic rectangles with minimal differentiation. No thumbnails, no visual preview of canvas contents. The empty state is plain. Compared to Lovart's rich project cards, the current cards feel like a spreadsheet.

---

## 8. Lovart Design Principles to Adopt

> [!NOTE]
> These are **design principles** extracted from studying Lovart's UI patterns. We are NOT copying Lovart's code, assets, branding, or visual identity.

### 8.1 Semantic Color System
Lovart uses a layered semantic token approach: `bg-base-default`, `bg-overlay-l1`, `bg-overlay-l2`, `text-default`, `text-secondary`, `text-tertiary`, `border-neutral-l1`, `border-neutral-l2`. Each token has a clear semantic meaning rather than a visual description.

**Adopt:** Create a unified `tokens.css` with semantic naming: `--color-bg-base`, `--color-bg-elevated`, `--color-bg-overlay`, `--color-text-primary`, `--color-text-secondary`, `--color-text-muted`, `--color-border-default`, `--color-border-subtle`.

### 8.2 Progressive Disclosure
Lovart hides complexity behind clean surfaces. The composer chat panel shows only what's needed — tool steps appear progressively. The canvas shows images cleanly with minimal chrome until interaction.

**Adopt:** Reduce always-visible controls. Show parameter panels on demand. Collapse secondary toolbars until needed.

### 8.3 Spatial Hierarchy via Elevation
Lovart uses subtle shadows, `backdrop-filter: blur()`, and layered backgrounds to create depth. Panels float above canvas with clear visual separation. Selected items have distinct highlight borders with corner handles.

**Adopt:** Standardize elevation levels: Level 0 (canvas), Level 1 (panels), Level 2 (popovers), Level 3 (modals). Each level has consistent shadow + blur treatment.

### 8.4 Typography Discipline
Lovart uses Inter for UI text at controlled sizes: 12px (captions), 13px (body), 14px (labels), 15px (buttons). Serif display font for headings. Consistent line-height (1.4–1.5).

**Adopt:** Define a type scale: `--font-xs: 11px`, `--font-sm: 12px`, `--font-base: 13px`, `--font-md: 14px`, `--font-lg: 16px`, `--font-xl: 20px`. Lock body to Inter at `--font-base`.

### 8.5 Generous Whitespace
Lovart gives elements room to breathe. Card padding is 12–16px. Section gaps are 24–32px. The canvas doesn't crowd controls against edges.

**Adopt:** Define spacing scale: `--space-1: 4px`, `--space-2: 8px`, `--space-3: 12px`, `--space-4: 16px`, `--space-6: 24px`, `--space-8: 32px`.

### 8.6 Clean Selection States
Lovart's selected canvas items show: blue/highlight outline, corner resize handles (small white squares with colored borders), type label above the frame ("Image", "800 × 1440").

**Adopt:** Redesign node selection: thinner highlight border, consistent corner handles, metadata label above selected node.

### 8.7 Unified Input Components
Lovart uses consistent rounded input fields with `border-radius: 22px` for the composer, `8px` for form fields. Focus state is a subtle border color change, not a full glow.

**Adopt:** Standardize input components with consistent border-radius, focus states, and padding.

### 8.8 Subtle Animations
Lovart uses `transition: all 150ms ease-out` consistently. No jarring snaps. Panels slide in smoothly. Hover states transition opacity and background.

**Adopt:** Standardize transition duration (150ms for interactions, 200ms for panels, 300ms for page transitions) and easing (`ease-out` for opens, `ease-in` for closes).

---

## 9. Recommended New UI Information Architecture

### 9.1 Design Token Unification

```
static/css/
├── tokens.css          ← [NEW] Unified design tokens (colors, spacing, typography, shadows, z-index)
├── components.css      ← [NEW] Shared UI components (buttons, inputs, cards, modals, badges)
├── theme.css           ← [MODIFY] Simplified to import tokens.css + minimal overrides
├── smart-canvas.css    ← [MODIFY] Remove token redeclarations, import tokens.css
├── canvas-list.css     ← [MODIFY] Remove token redeclarations, import tokens.css
├── asset-manager.css   ← [MODIFY] Remove token redeclarations, import tokens.css
└── api-settings.css    ← [MODIFY] Remove token redeclarations, import tokens.css
```

### 9.2 Z-Index Layer System

```css
/* In tokens.css */
:root {
    --z-canvas-nodes: 1;
    --z-canvas-selected: 10;
    --z-canvas-dragging: 12;
    --z-canvas-selection-box: 18;
    --z-floating-hud: 20;
    --z-composer: 30;
    --z-popover: 50;
    --z-panel: 55;
    --z-header-buttons: 56;
    --z-drawer: 57;
    --z-toast: 60;
    --z-menu: 75;
    --z-modal-backdrop: 85;
    --z-modal: 90;
    --z-lightbox: 96;
    --z-tooltip: 120;
}
```

### 9.3 Component Architecture (CSS-only, no framework)

| Component | Purpose | Shared Across |
|---|---|---|
| `.btn`, `.btn-primary`, `.btn-ghost`, `.btn-danger` | Unified button styles | All pages |
| `.input-field`, `.select-field` | Form input components | All pages |
| `.card`, `.card-elevated` | Surface containers | Canvas list, asset manager |
| `.modal-backdrop`, `.modal-panel` | Modal overlay system | All pages |
| `.panel-slide` | Slide-out drawer | Smart canvas, asset manager |
| `.badge`, `.pill` | Status indicators | All pages |
| `.toast` | Notification | All pages |

---

## 10. UI Redesign Risk Points

### 10.1 🔴 CRITICAL RISK — World Transform System
**Risk:** Any CSS change that affects `#shell` or `#world` sizing, padding, or transforms will break `screenToWorld()` coordinate calculations.
**Mitigation:** Never add padding, margin, border, or transform to `#shell`. Never wrap `#world` in additional containers. Test pan/zoom after every CSS change.

### 10.2 🔴 CRITICAL RISK — Node Position Persistence
**Risk:** Nodes use `style.left` and `style.top` in world pixels. If node containers are restructured, positions will drift.
**Mitigation:** `.image-node` must remain `position: absolute` inside `#world`. Never change `transform-origin` or add CSS transforms to nodes.

### 10.3 🔴 CRITICAL RISK — Connection Port Geometry
**Risk:** Connection line math calculates port positions using `.getBoundingClientRect()`. CSS changes to port positioning or node padding will misalign lines.
**Mitigation:** Test connections after any node styling change. Verify ports visually align with bezier endpoints.

### 10.4 🟡 HIGH RISK — CSS Variable Rename Cascade
**Risk:** Renaming `--page`, `--panel`, `--text`, etc. across all files simultaneously. A missed reference = broken styling.
**Mitigation:** Add new tokens alongside old ones first. Migrate references incrementally. Remove old tokens only after verification.

### 10.5 🟡 HIGH RISK — Z-Index Collision
**Risk:** Changing z-index values can cause modals to appear behind panels or popovers to be clipped.
**Mitigation:** Test every overlay type after z-index changes: toast, modal, popover, drawer, create menu, mention picker.

### 10.6 🟡 HIGH RISK — iframe Cross-Origin Theme Sync
**Risk:** If theme CSS structure changes, the `postMessage` theme sync between `index.html` and iframes may apply classes that no longer match CSS rules.
**Mitigation:** Keep `.theme-dark` class name unchanged. Theme switching must remain class-based.

### 10.7 🟢 MEDIUM RISK — Responsive Breakpoint Conflicts
**Risk:** New responsive styles may conflict with existing `@media` rules and `zoom: var(--studio-ui-scale)`.
**Mitigation:** Test at 100%, 125%, and 150% UI scale. Test window resize to mobile breakpoints.

### 10.8 🟢 MEDIUM RISK — Lucide Icon Refresh
**Risk:** Dynamic DOM rendering requires `lucide.createIcons()` after innerHTML updates. Missing this call = invisible icons.
**Mitigation:** Ensure all render functions call icon refresh after DOM insertion.

### 10.9 🟢 MEDIUM RISK — Tailwind CDN Conflicts
**Risk:** Tailwind utilities are used sparingly but some layout relies on them (`w-4`, `h-4`, `flex-shrink-0`). New styles must not conflict.
**Mitigation:** Prefer custom CSS for new components. Don't remove Tailwind CDN until all utility references are audited.

### 10.10 🟢 LOW RISK — IME Composition
**Risk:** CJK input method composition listeners in asset-manager.js protect search inputs from premature render during pinyin input. Any input component refactoring must preserve this.
**Mitigation:** Keep `compositionstart` / `compositionend` guards on all search inputs.

---

## 11. Recommended Implementation Phases

### Phase 1: Design Foundation (Estimated: 3–4 days)
**Goal:** Establish unified design token system and shared components without changing any layout or functionality.

**Scope:**
- Create `tokens.css` with unified color, spacing, typography, shadow, and z-index tokens
- Create `components.css` with shared button, input, card, badge, and toast components
- Update `theme.css` to import and align with new tokens
- Add new tokens alongside existing ones (backward compatible)
- NO layout changes, NO DOM changes, NO JS changes

**Success Criteria:** All pages render identically before and after. Light/dark theme work correctly.

---

### Phase 2: Canvas List Visual Refresh (Estimated: 2–3 days)
**Goal:** Modernize the project workspace with Lovart-inspired card styling, spacing, and typography.

**Scope:**
- Migrate `canvas-list.css` to use unified tokens
- Redesign `.ws-card` with richer visual treatment (subtle shadows, hover elevation, better typography)
- Improve `.ws-sidebar` spacing and project row styling
- Polish empty state design
- Improve dark theme contrast

**Success Criteria:** Canvas list looks polished. Pan/zoom/drag still work. Card creation and deletion work. Cross-project cut/paste works.

---

### Phase 3: Smart Canvas Chrome Refinement (Estimated: 4–5 days)
**Goal:** Improve the floating controls, toolbar, and panel styling without touching the canvas engine.

**Scope:**
- Migrate `smart-canvas.css` to use unified tokens (gradual, token-by-token)
- Redesign `.smart-back`, `#smartTitle`, header toggle buttons
- Improve `#minimap` styling
- Redesign `#createMenu` with cleaner menu appearance
- Improve `.floating-node-actions` toolbar
- Refine `#assetPanel` drawer styling

**Success Criteria:** All canvas operations work. Nodes drag, resize, connect. Composer generates. Asset panel opens/closes.

---

### Phase 4: Node Visual Polish (Estimated: 3–4 days)
**Goal:** Improve node appearance, selection states, and connection lines to match Lovart-level polish.

**Scope:**
- Redesign `.image-node` card styling (softer shadows, better border-radius, cleaner thumbnails)
- Improve `.selected` state (thinner highlight, corner handles like Lovart)
- Improve `.node-running` state animation
- Polish `.connection-layer` line styling (smoother curves, subtler colors)
- Improve `.image-name-badge` and `.run-time-pill` appearance

**Success Criteria:** Nodes look polished. All node types render correctly. Selection, drag, resize, and connections work.

---

### Phase 5: Composer & Panels Redesign (Estimated: 3–4 days)
**Goal:** Modernize the composer card, prompt input, and parameter panels.

**Scope:**
- Redesign `.composer-card` layout and styling
- Improve `#promptInput` with cleaner styling
- Redesign `.param-row` and dynamic parameter controls
- Polish `#promptPresetPanel` and `#promptTemplatePanel`
- Improve `#imageEditModal` toolbar and controls

**Success Criteria:** Generation workflow works end-to-end. All engines (API, Volcengine, ModelScope, ComfyUI, RunningHub) work. Presets and templates work.

---

### Phase 6: Asset Manager & API Settings Polish (Estimated: 3–4 days)
**Goal:** Align secondary pages with the new design system.

**Scope:**
- Migrate `asset-manager.css` to unified tokens
- Polish 3-column layout, card grid, detail panel
- Migrate `api-settings.css` to unified tokens
- Polish provider cards, form layout, modal overlays

**Success Criteria:** All CRUD operations work. Upload, search, batch operations work. Provider configuration saves correctly.

---

### Phase 7: App Shell & Navigation Redesign (Estimated: 2–3 days)
**Goal:** Modernize the `index.html` sidebar and stage area.

**Scope:**
- Redesign `#studioSidebar` with Lovart-inspired nav styling
- Improve `.stage` iframe viewport (border-radius, transitions)
- Polish update modal
- Improve mobile responsiveness

**Success Criteria:** All navigation works. Theme/language toggles work. Update flow works. All iframe pages load correctly.

---

## 12. Per-Phase File Change Estimates

### Phase 1: Design Foundation
| Action | File |
|---|---|
| **[NEW]** | `static/css/tokens.css` |
| **[NEW]** | `static/css/components.css` |
| **[MODIFY]** | `static/css/theme.css` — align with new tokens |
| **[MODIFY]** | `static/smart-canvas.html` — add `<link>` to tokens.css |
| **[MODIFY]** | `static/canvas-list.html` — add `<link>` to tokens.css |
| **[MODIFY]** | `static/asset-manager.html` — add `<link>` to tokens.css |
| **[MODIFY]** | `static/api-settings.html` — add `<link>` to tokens.css |
| **[MODIFY]** | `static/index.html` — add `<link>` to tokens.css |

---

### Phase 2: Canvas List Visual Refresh
| Action | File |
|---|---|
| **[MODIFY]** | `static/css/canvas-list.css` — token migration + visual redesign |
| **[MODIFY]** | `static/js/canvas-list.js` — update dynamic DOM class names if any new classes added |
| **[MODIFY]** | `static/canvas-list.html` — minor HTML adjustments if needed |

---

### Phase 3: Smart Canvas Chrome Refinement
| Action | File |
|---|---|
| **[MODIFY]** | `static/css/smart-canvas.css` — token migration + chrome styling |
| **[MODIFY]** | `static/smart-canvas.html` — minor HTML adjustments for new styling hooks |

---

### Phase 4: Node Visual Polish
| Action | File |
|---|---|
| **[MODIFY]** | `static/css/smart-canvas.css` — node, selection, connection styling |
| **[MODIFY]** | `static/js/smart-canvas.js` — update class names for new node states if any |

---

### Phase 5: Composer & Panels Redesign
| Action | File |
|---|---|
| **[MODIFY]** | `static/css/smart-canvas.css` — composer, panels, editor styling |
| **[MODIFY]** | `static/smart-canvas.html` — minor HTML restructuring for composer layout |
| **[MODIFY]** | `static/js/smart-canvas.js` — update dynamic DOM for new composer layout if needed |

---

### Phase 6: Asset Manager & API Settings Polish
| Action | File |
|---|---|
| **[MODIFY]** | `static/css/asset-manager.css` — token migration + visual polish |
| **[MODIFY]** | `static/js/asset-manager.js` — update dynamic render functions for new classes |
| **[MODIFY]** | `static/css/api-settings.css` — token migration + visual polish |
| **[MODIFY]** | `static/js/api-settings.js` — update dynamic render for new styling |

---

### Phase 7: App Shell & Navigation Redesign
| Action | File |
|---|---|
| **[MODIFY]** | `static/index.html` — sidebar restructuring + styling |
| **[MODIFY]** | `static/css/theme.css` — shell-level styling updates |

---

## Appendix A: Files Audited

| File | Size | Fully Read |
|---|---|---|
| `static/smart-canvas.html` | 41 KB | ✅ |
| `static/css/smart-canvas.css` | 208 KB | ✅ |
| `static/js/smart-canvas.js` | 988 KB | ✅ (sectional) |
| `static/canvas-list.html` | 5.6 KB | ✅ |
| `static/css/canvas-list.css` | 27 KB | ✅ |
| `static/js/canvas-list.js` | 48 KB | ✅ |
| `static/index.html` | 122 KB | ✅ |
| `static/css/theme.css` | 55 KB | ✅ |
| `static/js/theme.js` | 11 KB | ✅ |
| `static/asset-manager.html` | 2.8 KB | ✅ |
| `static/css/asset-manager.css` | 51 KB | ✅ |
| `static/js/asset-manager.js` | 267 KB | ✅ |
| `static/api-settings.html` | 47 KB | ✅ |
| `static/css/api-settings.css` | 202 KB | ✅ |
| `static/js/api-settings.js` | 212 KB | ✅ |
| `main.py` | 953 KB | ✅ (routes + static serving) |

## Appendix B: API Endpoints (Canvas-Related)

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/canvases` | List all active canvases |
| `POST` | `/api/canvases` | Create canvas |
| `GET` | `/api/canvases/{id}` | Get full canvas JSON |
| `PUT` | `/api/canvases/{id}` | Save canvas (optimistic lock) |
| `GET` | `/api/canvases/{id}/meta` | Get metadata only |
| `POST` | `/api/canvases/{id}/meta` | Update metadata |
| `DELETE` | `/api/canvases/{id}` | Soft delete |
| `POST` | `/api/canvases/{id}/restore` | Restore from trash |
| `DELETE` | `/api/canvases/{id}/purge` | Permanent delete |
| `GET` | `/api/canvases/trash` | List trashed canvases |
| `GET/POST` | `/api/projects` | Project CRUD |
| `WS` | `/ws/stats` | Real-time sync |
