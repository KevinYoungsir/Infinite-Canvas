# Infinite Canvas — Phase 2A: Workspace Shell & Canvas Entry Experience Specification

**Document Version:** 2.0.0-draft (Design Audit & Specification)
**Author Role:** Senior Product Designer + UI Systems Designer
**Scope:** Workspace Entry Experience (`canvas-list.html`, `canvas-list.css`, `canvas-list.js`, and Stage integration in `index.html`)
**Design Reference:** Lovart-inspired AI Creative Workspace principles (No asset / trademark duplication)
**Implementation Status:** ⚠️ **AUDIT ONLY — DO NOT IMPLEMENT PRODUCT CODE IN THIS PHASE**

---

## 1. Current Workspace Audit

The Infinite Canvas Workspace (`/static/canvas-list.html`) serves as the primary project and canvas launcher for the application. It is accessed either as an independent full page or embedded inside the `iframe#frame-canvas` container of `index.html`.

### 1.1 Architecture & DOM Map

```text
div#workspace.workspace
├── aside#sidebar.ws-sidebar
│   ├── div.ws-side-head
│   │   ├── div.ws-side-title ("项目" / "Projects")
│   │   └── button#newProjectBtn.ws-side-add (Icon: plus)
│   ├── div#newProjectRow.ws-newproj-row (Inline creation form)
│   │   ├── input#newProjectInput.ws-newproj-input
│   │   ├── button#newProjectConfirm.ws-mini-btn.primary (Icon: check)
│   │   └── button#newProjectCancel.ws-mini-btn (Icon: x)
│   ├── div#projectList.ws-project-list (Scrollable list container)
│   │   └── [Dynamic div.ws-project-row[data-project-id]]
│   │       ├── span.ws-project-icon (Icon: folder / folder-open)
│   │       ├── span.ws-project-name ("默认项目", etc.)
│   │       ├── span.ws-project-count (Badge number)
│   │       └── span.ws-project-actions (Hover actions)
│   │           ├── button.ws-proj-act.rename (Icon: pencil)
│   │           └── button.ws-proj-act.del (Icon: trash-2, non-default projects only)
│   └── div.ws-side-foot
│       └── button#trashEntry.ws-trash-entry
│           ├── i[data-lucide="trash-2"]
│           ├── span.ws-trash-label ("回收站" / "Trash")
│           └── span#trashBadge.ws-trash-badge ("0")
│
└── main.ws-main
    ├── div.ws-topbar (Header toolbar)
    │   ├── div.ws-topbar-left
    │   │   ├── div#boardProjectName.ws-board-name ("默认项目")
    │   │   └── span#boardCanvasCount.ws-board-count ("0")
    │   └── div.ws-topbar-right
    │       ├── button#pasteCanvasBtn.ws-paste-btn (Clipboard cut/paste, hidden by default)
    │       ├── button#boardResetView.ws-icon-btn (Locate/Center view)
    │       ├── button#boardRefresh.ws-icon-btn (Reload data)
    │       └── button#newCanvasBtn.ws-primary-btn (Primary CTA: "新建画布")
    │
    ├── div#board.ws-board (Pannable / zoomable virtual coordinate surface)
    │   ├── div#boardWorld.ws-board-world (World transform host: translate(X,Y) scale(S))
    │   │   ├── [Dynamic div.ws-card[data-canvas-id]] (Draggable canvas cards)
    │   │   │   ├── div.ws-card-top
    │   │   │   │   ├── span.ws-card-kind (.smart / .classic badge)
    │   │   │   │   └── button.ws-card-menu (Icon: more-horizontal)
    │   │   │   ├── div.ws-card-title (Text or inline rename input)
    │   │   │   ├── div.ws-card-meta (Footer metadata pill)
    │   │   │   │   ├── span.ws-card-nodes ("N 节点")
    │   │   │   │   ├── span.ws-card-meta-dot
    │   │   │   │   └── span.ws-card-time ("MM-DD HH:mm")
    │   │   │   └── div.ws-card-delete-confirm (Inline delete confirmation)
    │   │   └── [Dynamic div.ws-create-card] (Inline creation popover spawned at cursor)
    │   └── div#boardEmptyHint.ws-board-empty (Empty state placeholder)
    │       ├── div.ws-board-empty-icon
    │       ├── div.ws-board-empty-text ("暂无画布")
    │       ├── div.ws-board-empty-sub ("为当前项目创建第一块画布")
    │       └── div.ws-board-empty-actions
    │           └── button#emptyCreateCanvasBtn.ws-primary-btn
    │
    ├── div#trashPanel.ws-trash-panel (Full-board modal overlay)
    │   ├── div.ws-trash-head (Title + close button)
    │   ├── div.ws-trash-note (30-day auto-purge policy banner)
    │   └── div#trashList.ws-trash-list (Grid of .ws-trash-card items)
    │
    └── div#boardStatus.ws-status (Bottom toast notification)
```

### 1.2 CSS Selector Map (`canvas-list.css`)

| Selector Category | Existing Selectors |
|---|---|
| **Root & Layout** | `:root`, `.theme-dark`, `body`, `.workspace`, `html[data-studio-scale="off"].studio-scale-managed .workspace` |
| **Sidebar Components** | `.ws-sidebar`, `.ws-side-head`, `.ws-side-title`, `.ws-side-add`, `.ws-newproj-row`, `.ws-newproj-input`, `.ws-mini-btn`, `.ws-project-list`, `.ws-project-row`, `.ws-project-icon`, `.ws-project-name`, `.ws-project-name-input`, `.ws-project-count`, `.ws-project-actions`, `.ws-proj-act`, `.ws-project-confirm`, `.ws-side-foot`, `.ws-trash-entry`, `.ws-trash-badge` |
| **Main & Topbar** | `.ws-main`, `.ws-topbar`, `.ws-topbar-left`, `.ws-board-name`, `.ws-board-count`, `.ws-topbar-right`, `.ws-icon-btn`, `.ws-primary-btn`, `.ws-paste-btn` |
| **Board Virtual Stage** | `.ws-board`, `.ws-board.panning`, `.ws-board-world`, `.ws-board-empty`, `.ws-board-empty-icon`, `.ws-board-empty-text`, `.ws-board-empty-sub`, `.ws-board-empty-actions` |
| **Canvas Card System** | `.ws-card`, `.ws-card:hover`, `.ws-card.dragging`, `.ws-card.cc-marked`, `.ws-card.cut`, `.ws-card-top`, `.ws-card-icon`, `.ws-card-kind`, `.ws-card-menu`, `.ws-card-title`, `.ws-card-title-input`, `.ws-card-meta`, `.ws-card-meta-dot`, `.ws-card-time`, `.ws-card-nodes`, `.ws-card-actions`, `.ws-card-delete-confirm` |
| **Context Menus & Modals** | `.ws-card-pop`, `.ws-pop-item`, `.ws-pop-sep`, `.ws-pop-sub-title`, `.ws-pop-proj`, `.ws-pop-scroll`, `.ws-create-card`, `.ws-create-title`, `.ws-create-input`, `.ws-create-toggle`, `.ws-create-actions` |
| **Trash Management** | `.ws-trash-panel`, `.ws-trash-head`, `.ws-trash-note`, `.ws-trash-list`, `.ws-trash-empty`, `.ws-trash-card`, `.ws-trash-act`, `.ws-trash-confirm` |
| **Feedback** | `.ws-status`, `.ws-status.show` |

### 1.3 JavaScript Interaction Map (`canvas-list.js`)

```mermaid
graph TD
    A["loadAll() API"] --> B["renderProjects()"]
    A --> C["renderBoard()"]
    A --> D["refreshTrashCount()"]

    C --> E["buildCard(c)"]
    E --> F["attachCardDrag()"]
    F -->|Drag > 5px| G["persistMeta(board_x, board_y)"]
    F -->|Click < 5px| H["openCanvas(c) -> redirect"]

    E --> I["openCardMenu() -> Context Menu"]
    I --> J["Rename inline"]
    I --> K["Export JSON / ZIP with assets"]
    I --> L["Cut / Paste across projects"]
    I --> M["Delete -> Soft Delete API"]

    N["newCanvasBtn / emptyCreateCanvasBtn"] --> O["openCreateCard(worldPt)"]
    O --> P["createCanvasOnBoard() -> POST /api/canvases"]

    Q["Board Pan / Wheel"] --> R["applyViewport() -> transform: translate/scale"]
```

### 1.4 Visual & UX Problem Map

1. **Lack of AI Creative Workspace Identity:**
   The current UI presents as an engineering dashboard or database admin interface. There is no sense of creative momentum, visual canvas previews, or AI inspiration.
2. **Heavy "Boxy" Card Aesthetics:**
   `.ws-card` uses a rigid `248px × 150px` rectangle with a hard 1px border and dense text. It lacks thumbnail previews of the canvas contents, making all canvases look identical unless the user reads the textual title.
3. **Overly Aggressive Typographic Weight:**
   Font weights of `850` and `800` are applied ubiquitously (`.ws-side-title`, `.ws-board-name`, `.ws-board-count`, `.ws-primary-btn`, `.ws-card-title`, `.ws-card-kind`). This creates constant visual competition and high cognitive fatigue.
4. **Disjointed Radius System:**
   Some buttons use `border-radius: 8px`, badge counters use `999px`, card pills use `6px`, and popup menus use `8px`. The radius rhythm is arbitrary rather than systematic.
5. **Dark Mode Contrast Clashing:**
   In dark mode, active sidebar items and primary buttons turn `#d8dee9` with `#0f172a` text (`canvas-list.css:257`), creating jarring high-contrast blocks that break the subdued dark studio atmosphere.
6. **Weak and Clinical Empty State:**
   `.ws-board-empty` displays a generic `mouse-pointer-click` icon with "暂无画布". It fails to explain what an Infinite Canvas is, offers no templates, and does not inspire creative action.
7. **Board Virtual Stage Confusion:**
   Because the board features an infinite dot grid, new users often confuse the workspace board with the actual editor canvas. The relationship between "Workspace Board (Card Organizer)" and "Smart Canvas (Editor)" is not visually differentiated.

### 1.5 Interaction Safety Boundary

> [!CAUTION]
> During Phase 2, the boundary between presentation styling and behavioral runtime must be strictly maintained:

| Component | Behavior Contract (DO NOT TOUCH) | Presentation Contract (SAFE TO OVERRIDE) |
|---|---|---|
| `#board` & `#boardWorld` | Pointer events for Pan/Zoom, `applyViewport()`, `screenToWorld()`, `viewport.scale` calculation | Background color, radial dot grid pattern, grid contrast |
| `.ws-card` | Absolute positioning (`left`, `top` in world px), 5px drag threshold, click-to-open redirect | Background surface, border, border-radius, box-shadow, typography, thumbnail presentation |
| `.ws-card-menu` | Event stopPropagation, popup anchoring coordinates, action dispatch | Icon size, hover background, border-radius |
| `#newCanvasBtn` / `.ws-create-card` | Coordinate-based card creation, keyboard Enter/Esc dispatch, POST `/api/canvases` payload | Button styling, radius, typography, modal styling |
| `#projectList` & `.ws-project-row` | Selection click handler, inline input replacement on rename, `pendingDeleteProjectId` | Row height, hover highlight, active surface, badge typography |
| `#trashPanel` | 30-day retention API calls, restore/purge actions | Panel background, typography, button surfaces, spacing |

---

## 2. Information Architecture & Hierarchy Redesign

### 2.1 Current vs. Proposed Hierarchy

```text
CURRENT HIERARCHY (Engineering-focused)
Level 1: .workspace (Two-pane flex layout)
  ├── Level 2: .ws-sidebar (Project tree only)
  └── Level 2: .ws-main (Top bar + pannable card board)
        ├── Level 3: .ws-topbar (Title + 4 equal-weight utility buttons)
        └── Level 3: .ws-board (Pannable board with free-floating cards)
```

```text
PROPOSED HIERARCHY (Lovart-inspired Creative Studio)
Level 1: Workspace Shell
  ├── Level 2: Studio Navigation Sidebar (260px)
  │     ├── Header: Studio Brand & Quick New Canvas Action
  │     ├── Section A: Creative Views (All Canvases, Recent, Favorites)
  │     ├── Section B: Projects / Folders (Folder tree with subtle counts)
  │     └── Footer: Trash & Storage Health
  │
  └── Level 2: Studio Stage & Canvas Gallery
        ├── Level 3: Workspace Header (Breadcrumb / Title + View Mode + Primary CTA)
        ├── Level 4: Project Filter & Search Bar
        └── Level 5: Canvas Surface
              ├── State A: Populated Canvas Board / Gallery Grid
              │     └── Creative Canvas Cards (Thumbnail + Metadata + Actions)
              └── State B: Welcoming Empty State (Guidance + Quick Start Templates)
```

---

## 3. Lovart Design Principles & Infinite Canvas Application

| Lovart Studio Principle | Infinite Canvas Phase 2 Application |
|---|---|
| **Quiet, neutral work environment** | Eliminate colored backgrounds; use warm-neutral `#F5F5F4` (Light) and neutral deep charcoal `#121212` (Dark) from `ui-foundation.css`. |
| **Border over heavy drop shadow** | Replace bulky card shadows (`box-shadow: 0 16px 36px`) with crisp 1px borders (`--ui-border-default`) and delicate 4px micro-shadows (`--ui-shadow-sm`). |
| **Visual-first card presentation** | Shift cards from text-only boxes to media-aware cards with an integrated thumbnail preview area (or refined graphic placeholders for new canvases). |
| **High-priority, dignified CTA** | "New Canvas" becomes a high-visibility, elegant accent pill button with clear iconography and subtle hover elevation, without garish gradients. |
| **Deliberate typography scale** | Replace `850` font-weights with a disciplined ramp: `600` for titles, `500` for navigation labels, `400` for metadata. |
| **Soft spatial transitions** | Consistent `160ms cubic-bezier(.4, 0, .2, 1)` transitions on all cards, buttons, and row items. |

---

## 4. Component Design Specifications

### 4.1 Primary Action: "Create / New Canvas" CTA

The "New Canvas" button is the primary creative entry point.

```css
/* Specification for .ws-primary-btn */
.ws-primary-btn {
    height: 38px;
    padding: 0 16px;
    border-radius: var(--ui-radius-sm); /* 8px */
    background: var(--ui-accent);
    color: var(--ui-text-on-accent);
    font-size: var(--ui-text-sm);      /* 12px */
    font-weight: var(--ui-weight-semibold); /* 600 */
    border: 1px solid transparent;
    display: inline-flex;
    align-items: center;
    gap: var(--ui-space-2);            /* 8px */
    box-shadow: var(--ui-shadow-xs);
    transition: background var(--ui-duration-normal) var(--ui-ease-standard),
                transform var(--ui-duration-fast) var(--ui-ease-standard),
                box-shadow var(--ui-duration-fast) var(--ui-ease-standard);
}
.ws-primary-btn:hover {
    background: var(--ui-accent-hover);
    box-shadow: var(--ui-shadow-sm);
    transform: translateY(-1px);
}
.ws-primary-btn:active {
    transform: translateY(0);
}
.ws-primary-btn:focus-visible {
    outline: none;
    box-shadow: var(--ui-focus-ring);
}
```

### 4.2 Project Card System (`.ws-card`)

Cards must transition from a flat "database record" to a tangible "creative document".

```
┌────────────────────────────────────────────────┐
│  [Preview Thumbnail Area / Subtle Pattern]     │
│  Aspect Ratio: 16:9 or 3:2                     │
│  (Displays canvas snapshot or minimal badge)   │
├────────────────────────────────────────────────┤
│  Canvas Title                              [⋯] │
│  Kind Badge (Smart / Classic)                  │
│                                                │
│  19 nodes  •  Updated 2 hours ago              │
└────────────────────────────────────────────────┘
```

#### Card States
- **Default:** Solid surface (`--ui-bg-surface`), 1px border (`--ui-border-default`), 10px radius (`--ui-radius-md`), subtle shadow (`--ui-shadow-xs`).
- **Hover:** Border shifts to `--ui-border-strong`, elevation increases to `--ui-shadow-md`, transform lifts `translateY(-2px)`.
- **Dragging:** Cursor `grabbing`, shadow elevates to `--ui-shadow-floating`, opacity `0.95`, z-index `50`.
- **Context Menu Open:** Border locked to `--ui-border-strong`, shadow locked to `--ui-shadow-sm`.
- **Delete Confirming:** Surface transitions to `--ui-danger-soft`, border to `--ui-danger`, displaying inline confirm buttons.

### 4.3 Sidebar System (`.ws-sidebar`)

- **Width:** Fixed `260px` (contracted from 272px for better proportion).
- **Background:** `--ui-bg-surface-overlay` with `backdrop-filter: blur(20px)`.
- **Border:** Right 1px border `--ui-border-subtle`.
- **Project Rows (`.ws-project-row`):**
  - Height: `36px` (down from 40px for higher information density).
  - Radius: `8px` (`--ui-radius-sm`).
  - Active state: Subtle elevated surface `--ui-bg-soft` with text `--ui-text-primary` and left 3px accent bar, rather than an inverted black block.
  - Action icons (Rename, Delete): Clean ghost buttons appearing on hover with 14px Lucide icons.
- **Trash Entry (`.ws-trash-entry`):** Positioned at bottom with soft danger hover state.

### 4.4 Welcoming Empty State (`.ws-board-empty`)

```
┌─────────────────────────────────────────────────────────┐
│                          ┌───┐                          │
│                          │ ✦ │                          │
│                          └───┘                          │
│                    开启您的无限创意画布                 │
│   自由组织图像、视频与 AI 工作流，构建无边界的故事板    │
│                                                         │
│                  [ + 新建智能画布 ]                     │
└─────────────────────────────────────────────────────────┘
```

- **Title:** "开启您的无限创意画布" (Inspiring, creative).
- **Description:** "自由组织图像、视频与 AI 工作流，构建无边界的故事板。"
- **CTA:** Prominent primary button linking directly to create canvas.
- **Icon:** Subtle `sparkles` or `layout-grid` icon container with 12px radius and `--ui-bg-soft`.

---

## 5. Design Token Mapping for Phase 2

All styling in Phase 2 will exclusively consume tokens established in Phase 1 (`ui-foundation.css`):

| Workspace Element | Old Hardcoded Value | Mapped Design Token |
|---|---|---|
| Page Background | `#f6f7f9` / `#10141d` | `var(--ui-bg-canvas)` |
| Sidebar Surface | `rgba(255,255,255,.9)` | `var(--ui-bg-surface-overlay)` |
| Card Surface | `rgba(255,255,255,.98)` | `var(--ui-bg-surface)` |
| Card Surface (Raised/Hover) | `#fff` | `var(--ui-bg-surface-raised)` |
| Default Border | `#e5e9ef` / `#2d394c` | `var(--ui-border-default)` |
| Subtle Divider | `rgba(100,116,139,.18)` | `var(--ui-border-subtle)` |
| Primary Text | `#151922` / `#f4f7fb` | `var(--ui-text-primary)` |
| Secondary Text | `#5f6b7a` / `#c4cedb` | `var(--ui-text-secondary)` |
| Muted/Faint Text | `#98a2b3` / `#8c98aa` | `var(--ui-text-tertiary)` |
| Card Radius | `8px` | `var(--ui-radius-md)` (10px) |
| Button Radius | `8px` | `var(--ui-radius-sm)` (8px) |
| Badge Radius | `999px` / `6px` | `var(--ui-radius-pill)` (999px) |
| Standard Shadow | `0 6px 18px rgba(15,23,42,.06)` | `var(--ui-shadow-xs)` |
| Hover Shadow | `0 16px 36px var(--shadow-strong)`| `var(--ui-shadow-md)` |
| Dragging Shadow | `0 20px 48px var(--shadow-strong)`| `var(--ui-shadow-floating)` |

---

## 6. DOM Modification Budget (Safety Analysis)

To prevent runtime JavaScript breakage, every planned DOM adjustment is audited below:

| Proposed Change | Category | JS Selector Impact | Verdict |
|---|---|---|---|
| Link `ui-foundation.css` & `ui-canvas-list.css` in `canvas-list.html` | **SAFE DOM ADDITION** | None | ✅ Permitted in Phase 2B |
| Override `.ws-card` padding, typography, border, and shadows via CSS | **CSS ONLY** | None | ✅ Permitted in Phase 2B |
| Override `.ws-sidebar` width, row height, and active states via CSS | **CSS ONLY** | None | ✅ Permitted in Phase 2B |
| Override `.ws-topbar` buttons and header typography via CSS | **CSS ONLY** | None | ✅ Permitted in Phase 2B |
| Redesign `.ws-board-empty` text and icon markup in `canvas-list.html` | **SAFE DOM ADDITION** | Preserves `#boardEmptyHint` and `#emptyCreateCanvasBtn` IDs | ✅ Permitted in Phase 2B |
| Add a decorative thumbnail container inside `buildCard()` | **BEHAVIOR SENSITIVE** | Must not alter `.ws-card-top`, `.ws-card-menu`, or card mousedown propagation | ⚠️ Defer to Phase 2C or handle via pure CSS pseudo-elements |
| Restructure `#board` or `#boardWorld` | **DO NOT TOUCH** | Breaks `screenToWorld()`, `resetView()`, and card dragging | ❌ Strictly Forbidden |
| Alter `data-canvas-id` or `data-project-id` attributes | **DO NOT TOUCH** | Breaks project switching, rename, cut/paste, and deletion | ❌ Strictly Forbidden |

---

## 7. Recommended Implementation Sequence for Phase 2

When execution authorization is granted, Phase 2 should proceed in three disciplined sub-phases:

```text
Phase 2A (Current) ────► Phase 2B (Foundation & Chrome) ────► Phase 2C (Cards & Polish)
  [Audit & Spec]           - Create ui-canvas-list.css           - Card visual refresh
                           - Link tokens in canvas-list.html      - Empty state enhancement
                           - Sidebar & Topbar reskin             - Light/Dark theme QA
                           - Verify zero JS regression           - Baseline closeout
```

---

## 8. Verification & QA Checklist for Phase 2 Execution

When Phase 2 implementation begins, the following checks must pass:
- [ ] Server startup without errors
- [ ] Project switching (Sidebar click -> board re-renders)
- [ ] New project creation (Inline input -> Enter -> POST `/api/projects`)
- [ ] Project rename (Pencil icon -> inline edit -> persist)
- [ ] Project deletion (Trash icon -> confirmation -> canvases move to Default)
- [ ] Canvas board Pan (Drag on background -> smooth translation)
- [ ] Canvas board Zoom (Mouse wheel -> zoom centered on cursor)
- [ ] Reset View button (Centers all cards within view bounds)
- [ ] Card Drag vs Click (Drag > 5px moves card and saves position; Click < 5px opens editor)
- [ ] Card Context Menu (Rename, Export JSON, Export with assets, Cut, Delete)
- [ ] Cut & Paste across projects (Clipboard button appears -> moves canvas)
- [ ] Trash panel overlay (Open -> 30-day banner -> Restore / Purge)
- [ ] Light / Dark theme seamless toggle
- [ ] Browser Console: 0 JavaScript errors, 0 resource 404s
- [ ] Zero diff on `canvas-list.js`, `smart-canvas.js`, and `main.py`

---

## Phase 2B Implementation Notes

**Implementation branch:** `feature/ui-workspace-shell-v1`

### Scope delivered

- Added `static/css/ui-canvas-list.css` as an additive Workspace-only override layer.
- Loaded styles in the order `canvas-list.css` → `theme.css` → `ui-foundation.css` → `ui-canvas-list.css`.
- Migrated the Workspace canvas surface, 272px sidebar, topbar, primary CTA, secondary controls,
  floating menus, creation shell, trash shell, typography, focus states, and scrollbars to Phase 1
  `--ui-*` design tokens.
- Preserved the existing Workspace DOM, all IDs and data attributes, JavaScript event targets, and
  light/dark theme propagation.
- Kept the Project Card and empty-state structures frozen. Card overrides are limited to tokenized
  color, border, shadow, and typography; no dimensions, position model, or transforms were added.

### Geometry and runtime safety

- `#board` receives background properties only. Its padding, margin, border, position, dimensions,
  and transform remain controlled by the existing stylesheet/runtime.
- `#boardWorld` receives no Phase 2B override.
- `.ws-card` receives no width, height, position, inset, padding, margin, or transform override.
- `screenToWorld`, `applyViewport`, viewport state, drag thresholds, `board_x`, and `board_y` are unchanged.
- `static/js/canvas-list.js`, `static/js/smart-canvas.js`, and `main.py` have zero diff.
- Override audit: `!important` 0; `pointer-events` 0; `z-index` 0; `transform` declarations 0;
  geometry-affecting overrides on `#board`, `#boardWorld`, and `.ws-card` 0.

### Browser QA

Real Chrome verification covered Workspace load, populated project/card rendering, pan, cursor-centered
zoom, reset view, card drag, `board_x`/`board_y` persistence after reload, card click/open and return,
New Canvas creation, project creation and switching, Paste visibility/action, Refresh, Trash overlay,
context menu, and both Light and Dark themes. Temporary QA project/canvas records were removed by their
exact IDs after the checks. Browser console errors: 0. The Workspace HTML, legacy CSS, foundation CSS,
Phase 2B CSS, and JavaScript resources all returned HTTP 200.

### Screenshot evidence

Light-before, Light-after, Dark-before, and Dark-after states were visually captured and verified via controlled Chrome CDP session. High-resolution screenshots are preserved under `docs/ui-redesign/screenshots/`.

---

## 9. Phase 2C Specification: Canvas Entry Cards & First-Run Experience

**Sub-phase:** Phase 2C-A (Design Audit & Specification)
**Target:** Canvas Entry Cards (`.ws-card`) + First-Run / Empty State Experience (`#boardEmptyHint`)
**Design Reference:** Lovart-inspired Minimalist AI Studio / Content-First Workspace
**Status:** AUDIT COMPLETE — SPECIFICATION FROZEN — ZERO PRODUCTION CODE MODIFIED

### 9.1 Capability Audit

An exhaustive audit of `canvas-list.html`, `canvas-list.js`, `canvas-list.css`, `ui-canvas-list.css`, and the backend implementation in `main.py` (`list_canvases()`, `canvas_record()`, SQLite / JSON files) confirms the status of all candidate canvas fields:

| Field Name | Source / Type | Status | Phase 2C Applicability |
|---|---|---|---|
| `canvas id` | `c.id` (str) | **AVAILABLE NOW** | Internal key; used for dataset and DOM selection; hidden from visual card |
| `canvas title` | `c.title` (str) | **AVAILABLE NOW** | Primary visual anchor; editable inline |
| `project id` | `c.project` (str) | **AVAILABLE NOW** | Used for filtering; not displayed on card (already in project context) |
| `created time` | `c.created_at` (int ms) | **AVAILABLE NOW** | Fallback for time formatting |
| `updated time` | `c.updated_at` (int ms) | **AVAILABLE NOW** | Secondary metadata; displayed in human relative time |
| `node count` | `c.node_count` (int) | **AVAILABLE NOW** | Secondary metadata; key metric for canvas scale |
| `canvas kind` | `c.kind` ("smart" \| "classic") | **AVAILABLE NOW** | Visual kind badge (Smart vs Classic) |
| `accent color` | `c.color` (str) | **AVAILABLE NOW** | Left border / tag indicator (`.cc-marked`) |
| `pinned state` | `c.pinned` (bool) | **AVAILABLE NOW** | Sort priority; optional pin badge |
| `owner` | `c.owner` (str) | **AVAILABLE NOW** | Single-user local app; hidden to avoid clutter |
| `board position` | `c.board_x`, `c.board_y` (float) | **AVAILABLE NOW** | World coordinate absolute positioning (`left`, `top`) |
| `node types` | `nodes[i].type` in canvas JSON | **DERIVABLE WITHOUT SCHEMA CHANGE** | Stored in individual JSON files; **NOT** in `/api/canvases` list response |
| `image count` | Extracted from image nodes | **DERIVABLE WITHOUT SCHEMA CHANGE** | Not exposed in `/api/canvases` list response |
| `text count` | Extracted from text nodes | **DERIVABLE WITHOUT SCHEMA CHANGE** | Not exposed in `/api/canvases` list response |
| `workflow count` | Extracted from workflow nodes | **DERIVABLE WITHOUT SCHEMA CHANGE** | Not exposed in `/api/canvases` list response |
| `generation count`| Extracted from run logs | **DERIVABLE WITHOUT SCHEMA CHANGE** | Not exposed in `/api/canvases` list response |
| `canvas dimensions`| Bounding box of all nodes | **DERIVABLE WITHOUT SCHEMA CHANGE** | Not calculated or exposed in list response |
| `first / last image`| Output URL from node runs | **DERIVABLE WITHOUT SCHEMA CHANGE** | Not aggregated or exposed in list response |
| `status` | Async execution state | **NOT AVAILABLE** | No board-level daemon status tracking |
| `cover / thumbnail` | Rasterized canvas image | **NOT AVAILABLE** | No snapshot engine or rasterized preview exists anywhere |
| `preview / snapshot`| Viewport capture | **NOT AVAILABLE** | No background canvas renderer exists |
| `last opened` | Access timestamp | **NOT AVAILABLE** | Only `updated_at` is tracked on save |
| `description` | Textual canvas summary | **NOT AVAILABLE** | No description field in schema or UI |

### 9.2 Available Canvas Metadata (`/api/canvases` Payload)

Each item returned by `GET /api/canvases` conforms to `canvas_record()` (`main.py:3925`):
```json
{
  "id": "qa-canvas-example",
  "title": "Phase 2C QA Canvas",
  "icon": "🧩",
  "kind": "smart",
  "owner": "",
  "color": "",
  "pinned": false,
  "project": "default",
  "board_x": 40.0,
  "board_y": 40.0,
  "created_at": "<qa-timestamp>",
  "updated_at": "<qa-timestamp>",
  "deleted_at": 0,
  "node_count": 19
}
```

### 9.3 Thumbnail Capability Gate

- **Result:** `REAL THUMBNAIL CAPABILITY: NO`
- **Gate Findings:**
  1. **Storage:** There is no thumbnail folder in the project filesystem (no `data/thumbnails` or similar).
  2. **Generation:** Neither `smart-canvas.js` nor `canvas.js` possesses a canvas screenshot/rasterization routine (no `toDataURL` or headless capture on save).
  3. **Backend:** `/api/canvases` returns 0 image URLs or thumbnail paths.
  4. **Performance Risk:** Dynamically opening 20+ canvas JSON files to locate image nodes during list loading would cause severe I/O degradation.
- **Strict Directive:**
  - Phase 2C **MUST NOT** rely on real thumbnails.
  - Phase 2C **MUST NOT** introduce fake image placeholders (no empty gray camera boxes, no random pastel gradients pretending to be artworks, no synthetic SVG illustrations).
  - The card system must stand on its own as a premium, typography-led, content-first metadata document.

### 9.4 Card Information Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  [Smart / Classic Badge]                         [ ··· Menu ]│
│                                                             │
│  Canvas Title (15px Semibold, Max 2 Lines)                 │
│                                                             │
│  19 nodes  •  Updated 2 hours ago                           │
└─────────────────────────────────────────────────────────────┘
```

#### 1-Second Visual Cognition Hierarchy
1. **Primary Layer (0–300ms):**
   - **Canvas Title:** The user's primary mental index. 15px, `font-weight: 600`, `--ui-text-primary`. High contrast, crisp line-height (1.3), graceful 2-line ellipsis.
   - **Kind Badge:** Semantic recognition (`.smart` vs `.classic`). Smart canvases receive a gentle indigo tint; classic canvases receive neutral subtle soft gray.
2. **Secondary Layer (300ms–800ms):**
   - **Scale / Content Density:** `c.node_count` ("19 节点"). Immediately informs the user whether this is a rich working canvas or an empty test stub. If 0 nodes, styled in `--ui-text-tertiary` as "0 节点".
   - **Recency / Freshness:** `formatCanvasTime(c.updated_at)` ("09/04 13:51" or relative). Tells the creator which canvas was touched most recently.
   - **Color / Pin Accent:** If `c.color` is marked, a refined 3px left border accent or badge dot indicates custom tagging.
3. **Tertiary Layer (On-demand / Hover):**
   - **Action Menu (`···`):** Context menu trigger button, positioned at top-right. Subtle ghost style, high affordance on hover.
   - **Inline Delete Confirm:** In-situ confirmation surface (`.ws-card-delete-confirm`) avoiding disruptive alert popups.

#### Noise Exclusion (What is NOT shown)
- Internal UUID / canvas hash (zero cognitive value).
- Blank owner strings or "default" user labels (single-player desktop studio).
- Absolute board coordinates (internal layout math).
- Technical runtime timestamps (raw epoch ms).

### 9.5 Recommended Card Strategy: Option B (Metadata-Driven Creative Card)

- **Option A (Real Thumbnail):** REJECTED — No thumbnail capability exists in the product.
- **Option B (Metadata-Driven Creative Card):** **RECOMMENDED FOR PHASE 2C**
  - Relies 100% on existing, reliable metadata fields.
  - Focuses on crisp typographic hierarchy, micro-borders, surface layering, and responsive hover feedback.
  - Aligns with Lovart's quiet, dignified document card aesthetic.
  - Zero performance overhead, zero backend changes, zero broken-image risk.
- **Option C (Hybrid Progressive Preview):** ADOPTED AS ARCHITECTURAL ROADMAP
  - The DOM structure and CSS classes are designed so that if a future Phase 3 thumbnail engine is introduced, a thumbnail container can be inserted seamlessly above the title without breaking card layout contracts.

### 9.6 Card States (Strict Draggable Object Rules)

> [!CAUTION]
> `.ws-card` is an absolutely positioned world-coordinate object within `#boardWorld` which has a global viewport matrix transform.
> **ABSOLUTELY NO `transform`, `translate`, OR `scale` IS PERMITTED ON `:hover`, `:active`, OR `.dragging`!**

| State | Styling Specification (Zero Geometry Impact) |
|---|---|
| **Default** | Background: `var(--ui-bg-surface)`; Border: `1px solid var(--ui-border-default)`; Radius: `var(--ui-radius-md)` (10px); Shadow: `var(--ui-shadow-xs)`. |
| **Hover** | Border: `1px solid var(--ui-border-strong)`; Shadow: `var(--ui-shadow-md)`; Menu button opacity: `1.0`. **NO `translateY` or `scale`!** |
| **Pressed / Mousedown** | Background: `var(--ui-bg-surface-raised)`; Shadow: `var(--ui-shadow-xs)`. |
| **Focused (`:focus-visible`)** | Outline: none; Box-shadow: `var(--ui-focus-ring)`. |
| **Dragging (`.dragging`)** | Cursor: `grabbing`; Shadow: `var(--ui-shadow-floating)`; Opacity: `0.92`. |
| **Context Menu Open** | Border: `1px solid var(--ui-border-strong)`; Shadow: `var(--ui-shadow-sm)`. |
| **Empty Metadata (0 nodes)**| Node count rendered in `var(--ui-text-tertiary)`. |
| **Color Marked (`.cc-marked`)**| Left border: `3px solid var(--ui-accent)` or user color tag. |

### 9.7 Geometry Decision: KEEP 248px × 150px

- **Dimension:** Fixed width `248px`, fixed height `150px`.
- **Layout Stride:** In `canvas-list.js:363`:
  - `XSTRIDE = 276px` (248px card + 28px horizontal gap)
  - `YSTRIDE = 176px` (150px card + 26px vertical gap)
- **Rationale for Preserving Geometry:**
  1. **Persistence Safety:** Users' existing canvases have saved `board_x` and `board_y` coordinates calculated from this stride. Resizing cards would cause visual overlap on populated boards.
  2. **Codebase Freeze:** Changing card dimensions would require modifying frozen layout constants in `canvas-list.js`.
  3. **Visual Proportion:** An aspect ratio of `248:150` (~1.65:1) closely mirrors the golden ratio (1.618:1) and comfortably accommodates the 3-tier information architecture without crowding.

### 9.8 Empty State Logic & Lifecycle

- **DOM Elements:** `#boardEmptyHint` containing `#emptyCreateCanvasBtn`.
- **Control Mechanism:** `canvas-list.js:383`:
  ```javascript
  const items = canvasesInProject(currentProjectId);
  boardEmptyHint.classList.toggle('hidden', items.length > 0);
  ```
- **Loading Safety:** `<div id="boardEmptyHint" class="ws-board-empty hidden">` defaults to `hidden` in static HTML. During initial API loading, it does not flash.
- **Pointer Events:** `.ws-board-empty` has `pointer-events: none` allowing background board drag-to-pan, while `.ws-board-empty-actions` has `pointer-events: auto` ensuring the button is clickable.
- **Click Behavior:** `canvas-list.js:1003` maps the center of the viewport to world coordinates via `screenToWorld()` and opens the inline creation popover at the center of the user's view.

### 9.9 First-Run Experience

When a user launches Infinite Canvas for the first time, or enters an empty project, the empty state must orient and inspire:
1. **Immediate Recognition:** Understand within 2 seconds that this is an AI Creative Studio, not an empty database.
2. **Clear Value Proposition:** Communicate that canvases are boundless spaces for multimodality (image, video, text, workflows).
3. **Frictionless Action:** One primary button directly centered in view to launch the first canvas.
4. **Lightweight Capability Cues:** Subtle icon badges representing core creative verbs:
   - ✦ **生成 (Generate):** Multi-model image & video generation
   - ☍ **连接 (Connect):** Node-based visual workflows
   - ⤢ **无限 (Infinite):** Unbounded spatial storyboards

### 9.10 Empty State Copy Options

- **Direction 1 (Direct & Productive — Recommended):**
  - **Title:** `开启第一块无限画布`
  - **Description:** `在一个无边界工作台中自由编排灵感、生成多模态内容并连接 AI 工作流。`
  - **Primary CTA:** `+ 新建智能画布`
- **Direction 2 (Minimal & Studio):**
  - **Title:** `探索无限创作空间`
  - **Description:** `自由组织图像、视频与节点，构建你的视觉故事板。`
  - **Primary CTA:** `+ 创建画布`
- **Direction 3 (Iterative & Creative):**
  - **Title:** `从一块空白画布开始`
  - **Description:** `连接模型与节点，让每一次灵感生成都有迹可循。`
  - **Primary CTA:** `+ 立即开始创作`

### 9.11 Create Canvas Entry Hierarchy

```text
               ┌────────────────────────────────────────────────────────┐
               │ Topbar Header                                          │
               │ [Project Name]           [Reset] [Refresh] [New Canvas]│◄── Persistent Primary Anchor
               └────────────────────────────────────────────────────────┘
                                           │
             ┌─────────────────────────────┴─────────────────────────────┐
             ▼ (When Board is Empty)                                     ▼ (When Board has Canvases)
┌────────────────────────────────────────┐                   ┌────────────────────────────────────────┐
│ Empty State Stage                      │                   │ Populated Board World                  │
│                                        │                   │                                        │
│          ✦ 开启第一块无限画布          │                   │  ┌──────────┐   ┌──────────┐           │
│   在无边界工作台中自由编排与生成内容   │                   │  │ Card A   │   │ Card B   │           │
│                                        │                   │  └──────────┘   └──────────┘           │
│         [ + 新建智能画布 ]             │◄── Focal CTA      │                                        │
│                                        │                   │  (Double-click or Context click)       │◄── Contextual
└────────────────────────────────────────┘                   └────────────────────────────────────────┘
```

1. **Focal Primary (Empty Board):** Center `#emptyCreateCanvasBtn` commands 100% visual attention.
2. **Persistent Primary (Populated Board):** Top-right `#newCanvasBtn` serves as the constant toolbar anchor.
3. **Contextual Action:** Double-click or right-click on board invokes `openCreateCard(worldPt)` at cursor.
All three routes converge into the identical creation pipeline (`openCreateCard() -> POST /api/canvases`).

### 9.12 Sidebar Width Decision: KEEP 272px

- **Audit Finding:**
  - Project names support up to 60 characters (`maxLength = 60`).
  - Row horizontal footprint: 20px folder icon + 8px gap + title + 24px count badge + 48px action icons + 24px padding = 124px fixed overhead.
  - At 272px: 148px available for text (~11 Chinese characters without truncation).
  - At 260px: 136px available for text (~9 Chinese characters without truncation).
- **UX Conclusion:** **KEEP 272px**.
  Shrinking the sidebar by 12px offers zero meaningful gain to the stage (1168px vs 1180px, <1% delta), while noticeably increasing project name truncation and crowding hover buttons. 272px is proven stable across all existing responsive breakpoints.

### 9.13 Design Token Mapping

All Phase 2C visual enhancements exclusively utilize the existing `--ui-*` token foundation:

| Component / Element | Token Applied | Visual Value (Light / Dark) |
|---|---|---|
| Card Surface | `var(--ui-bg-surface)` | `#FFFFFF` / `#1A1A1A` |
| Card Border (Default) | `var(--ui-border-default)` | `rgba(0,0,0,0.10)` / `rgba(255,255,255,0.08)` |
| Card Border (Hover) | `var(--ui-border-strong)` | `rgba(0,0,0,0.22)` / `rgba(255,255,255,0.18)` |
| Card Shadow (Default) | `var(--ui-shadow-xs)` | `0 1px 2px rgba(0,0,0,0.04)` |
| Card Shadow (Hover) | `var(--ui-shadow-md)` | `0 4px 12px rgba(0,0,0,0.08)` |
| Card Shadow (Dragging) | `var(--ui-shadow-floating)` | `0 16px 36px rgba(0,0,0,0.20)` |
| Card Title Typography | `var(--ui-text-primary)`, `600`, `15px` | High contrast, bold clarity |
| Node / Time Typography | `var(--ui-text-tertiary)`, `400`, `12px` | Subdued metadata |
| Smart Kind Badge | Background: `rgba(99,102,241,0.08)`; Text: `#6366F1` | Refined accent tint |
| Classic Kind Badge | Background: `var(--ui-bg-soft)`; Text: `var(--ui-text-secondary)` | Neutral subtle pill |
| Empty State Icon Surface | `var(--ui-bg-surface)`, `var(--ui-border-default)` | 48px rounded icon badge |
| Empty State Title | `var(--ui-text-primary)`, `600`, `18px` | Welcoming header |
| Empty State Subtitle | `var(--ui-text-secondary)`, `400`, `13px` | Explanatory copy |

### 9.14 DOM Modification Budget

| Target Change | Classification | JS Runtime Impact | Allowed in Phase 2C? |
|---|---|---|---|
| Refine card CSS (padding, border, shadows, typography) | **CSS ONLY** | None | ✅ Yes |
| Refine empty state CSS (icon size, spacing, typography) | **CSS ONLY** | None | ✅ Yes |
| Enrich `#boardEmptyHint` HTML copy & value proposition | **SAFE DOM ADDITION** | Preserves `#boardEmptyHint` and `#emptyCreateCanvasBtn` | ✅ Yes |
| Wrap card title & meta in semantic layout containers | **SAFE DOM ADDITION** | Preserves `.ws-card-title`, `.ws-card-menu`, `.ws-card-meta` | ✅ Yes |
| Card Drag / Click event listeners (`attachCardDrag`) | **BEHAVIOR SENSITIVE** | 5px movement threshold must be preserved | ⚠️ Do not modify logic |
| Board pan / zoom transform math (`applyViewport`) | **DO NOT TOUCH** | Critical coordinate system | ❌ Strictly Forbidden |
| `data-canvas-id` attribute on `.ws-card` | **DO NOT TOUCH** | Project management / deletion dependency | ❌ Strictly Forbidden |

### 9.15 Safety Boundaries

The following components remain **STRICTLY FROZEN**:
- `static/js/canvas-list.js` (core viewport, event bus, drag detection, API fetch)
- `static/js/smart-canvas.js` (editor coordinate engine, undo stack, node graph)
- `main.py` (FastAPI routes, SQLite/JSON persistence, ZIP export)
- Schema definitions (no new fields, no schema migrations)

### 9.16 Recommended Phase 2C Implementation Sequence

```text
Step 1: Safe DOM Enhancement in static/canvas-list.html
  └── Update #boardEmptyHint copy with Direction 1 text and capability badges.
      Keep #boardEmptyHint, #emptyCreateCanvasBtn, and .hidden class intact.

Step 2: Additive CSS Overrides in static/css/ui-canvas-list.css
  └── Card Reskin:
      - Clean 10px radius, 1px subtle border, micro-shadow.
      - Refine typography: title 15px/600, badge 11px/500, meta 12px/400.
      - Strictly NO transform/translate on hover/active.
  └── Empty State Polish:
      - 48px rounded icon container with soft accent border.
      - Dignified 18px title + 13px description.
      - Center-aligned CTA with 10px radius and solid primary accent.

Step 3: Comprehensive Visual & Smoke QA
  └── 1440px desktop testing in Light and Dark themes.
  └── Card drag test (>5px drag moves card; <5px click opens canvas).
  └── Empty state test (project with 0 canvases shows empty hint; clicking CTA creates canvas).
  └── Verify zero console errors, zero 404s, zero git diff on JS/Python.
```

### 9.17 QA Checklist for Phase 2C Closeout

- [ ] Card geometry preserved at `248px × 150px`
- [ ] No `transform` or `translate` on card `:hover` / `:active`
- [ ] Card drag vs click threshold (5px) works reliably
- [ ] Card title supports 1-line and 2-line rendering without overflowing 150px card height
- [ ] Card action menu (`···`) triggers without moving card or opening canvas
- [ ] Card inline delete confirmation functions correctly
- [ ] Empty state appears automatically when project canvas count is 0
- [ ] Empty state button `#emptyCreateCanvasBtn` successfully opens canvas creation popover at viewport center
- [ ] Empty state copy is professional, inspiring, and AI-native
- [ ] Light Theme: warm neutral `#F5F5F4` background, crisp borders, no heavy shadows
- [ ] Dark Theme: neutral charcoal `#121212` background, soft micro-borders, zero glare
- [ ] 0 console errors, 0 resource 404s
- [ ] Zero diff on `canvas-list.js`, `smart-canvas.js`, and `main.py`

### 9.18 Future Preview Capability (Phase 3+ Roadmap)

If real canvas thumbnails are prioritized in a future milestone, the recommended architecture is:
1. **Client-Side Offscreen Capture on Save:** In `smart-canvas.js:saveCanvas()`, render an offscreen 320×180 thumbnail of the active bounding box using HTML Canvas drawing or SVG foreignObject.
2. **Dedicated Storage Endpoint:** Upload webp/jpeg to `/assets/thumbnails/{canvas_id}.webp`.
3. **Non-blocking Persistence:** Save path in `canvas.thumbnail` without slowing down the primary JSON save.
4. **List API Extension:** Expose `thumbnail: str` in `canvas_record()`.
5. **Card Container Drop-in:** Option C's reserved thumbnail area in `.ws-card` immediately consumes the URL with progressive blur-up loading.
