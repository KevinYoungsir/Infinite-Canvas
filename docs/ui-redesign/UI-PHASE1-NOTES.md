# Infinite Canvas — Phase 1 Engineering & Design Notes

**Audit & Implementation Date:** 2026-09-03
**Target Branch:** `feature/ui-lovart-redesign-v1`
**Engineer:** Senior UI Engineer + Product Designer

---

## 1. Issues Identified in Phase 1

1. **Inline CSS Rules Scattered in HTML:**
   Several modals and containers contain hardcoded inline styles (e.g. `style="display:none"`, `style="aspect-ratio: ..."`), which occasionally require `!important` flags in overrides if not scoped strictly.
2. **Heavy Font-Weights Across Legacy CSS:**
   The original `smart-canvas.css` relied heavily on font-weights like `750`, `800`, `850`, and `900`. While our Phase 1 override normalized the HUD and top headers to `500` and `600`, internal node badges and sub-labels still inherit these heavy weights from legacy classes.
3. **Hardcoded Z-Index Magic Numbers:**
   Over 20 distinct z-index layers exist between `0` and `120`. While documented in `--ui-z-*` tokens, they cannot yet be safely replaced by CSS variables because some JavaScript routines query or alter element z-indexes during runtime dragging (`draggingState`).
4. **415 Media Preview Errors in Console:**
   During automated headless tests, several video thumbnail requests (`/api/media-preview?w=768&url=...mp4`) returned HTTP 415. This is an existing backend ffmpeg video-preview capability issue on certain legacy video filenames, unrelated to UI stylesheets.

---

## 2. Unresolved Items (Deferred by Design)

1. **AI Composer Card Internal Structure:**
   The prompt input, dynamic parameter strip, and cascade action buttons were only cosmetically reskinned (surface, border, radius, typography). The underlying grid areas (`"head head" "thumbs thumbs" "prompt-preview prompt-preview" "prompt prompt" "params run"`) remain untouched to avoid disrupting parameter toggling.
2. **Node Selection Ring Styling:**
   The current selection state uses `.image-node.selected:not(.empty-node) .image-wrap > img { border-color: var(--strong); box-shadow: 0 0 0 1px var(--strong); }`. A Lovart-inspired corner-handle selection frame will be introduced in Phase 4 once the node container architecture is modernized.
3. **Minimap Internal Content Dimensions:**
   The minimap HUD border, radius, and background were reskinned, but the internal canvas coordinate projection remains identical to preserve tracking accuracy.

---

## 3. High-Risk / Do-Not-Touch Areas Confirmed

The following areas were validated as strictly non-negotiable across all redesign phases:

1. **`#shell` and `#world` Containers:**
   `screenToWorld(e)` computes:
   $$\text{worldX} = \frac{\text{clientX} - \text{shellRect.left} - \text{viewport.x}}{\text{viewport.scale}}$$
   Any padding, margin, border, or transform applied to `#shell` will instantly cause cursor drift during node dragging and canvas panning.
2. **`html[data-studio-scale="off"]`:**
   Must remain present on `smart-canvas.html` so that `theme.js` does not apply global `zoom` to `document.body`, which breaks pointer math.
3. **DOM Selector Contracts:**
   All `data-smart-node-action`, `data-smart-group-action`, `data-param`, `data-comfy-*`, `data-rh-*`, and class-based hooks (`.node-port.port-in`, `.node-resize-handle`) must not be renamed or restructured.

---

## 4. Recommended Scope for Phase 2: Workspace Shell (Canvas List)

For Phase 2, we recommend focusing on the **Canvas List & Project Workspace (`canvas-list.html`, `canvas-list.css`, `canvas-list.js`)**:

1. **Token Integration:**
   Link `ui-foundation.css` in `canvas-list.html` and create `static/css/ui-canvas-list.css` to override legacy variables with `--ui-*`.
2. **Canvas Card Modernization (`.ws-card`):**
   - Apply `--ui-radius-lg` (12px) and `--ui-border-default`.
   - Implement clean hover elevation using `--ui-shadow-md` and `--ui-border-strong`.
   - Refine node count and timestamp typography with `--ui-text-tertiary` and `--ui-weight-medium`.
3. **Workspace Sidebar Polish (`.ws-sidebar`):**
   - Reskin project folder items with `--ui-bg-hover` and `--ui-accent` active states.
   - Improve trash entry counter badge styling.
4. **Empty State Enhancement (`.ws-board-empty`):**
   - Replace the current sparse empty hint with a refined, centered card using `--ui-bg-surface-raised` and modern CTA buttons.
5. **Zero JavaScript Regression:**
   - Preserve virtual viewport math (`screenToWorld`, `applyViewport`, `viewport = {x, y, scale}`).
   - Preserve drag-vs-click 5px threshold.
   - Preserve offline ZIP packaging engine.
