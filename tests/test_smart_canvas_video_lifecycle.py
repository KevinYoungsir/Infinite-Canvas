import unittest
from pathlib import Path


SMART_CANVAS_JS = (
    Path(__file__).resolve().parents[1] / "static" / "js" / "smart-canvas.js"
).read_text(encoding="utf-8")


def source_between(start, end, source=SMART_CANVAS_JS):
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


class SmartCanvasVideoLifecycleTests(unittest.TestCase):
    def assert_selection_only_update(self, source):
        self.assertIn("syncSelectionUi();", source)
        self.assertIn("updateComposer();", source)
        self.assertNotIn("render();", source)

    def test_blank_canvas_click_does_not_render_nodes(self):
        handler = source_between("shell.onclick = e => {", "minimap?.addEventListener")
        self.assertIn("clearSelection();", handler)
        self.assert_selection_only_update(handler)

    def test_node_selection_click_does_not_render_nodes(self):
        bind_node_events = source_between(
            "function bindNodeEvents(){",
            "function rectOverlapNode",
        )
        handler = source_between(
            "        el.onclick = e => {",
            "        if(nodeForControls?.type !== 'smart-group')",
            bind_node_events,
        )
        self.assert_selection_only_update(handler)

    def test_marquee_selection_does_not_render_nodes(self):
        handler = source_between(
            "function finishSelection(event){",
            "function createSmartGroupFromNodes",
        )
        self.assert_selection_only_update(handler)

    def test_document_click_panel_cleanup_does_not_render_nodes(self):
        close_handler = source_between(
            "function closePromptTemplatePanel(){",
            "function applyPromptTemplateToNode",
        )
        open_handler = source_between(
            "async function openPromptTemplatePanel",
            "function closePromptTemplatePanel",
        )
        self.assertIn("syncPromptTemplateButtons();", close_handler)
        self.assertNotIn("render();", close_handler)
        self.assert_selection_only_update(open_handler)
        self.assertIn("syncPromptTemplateButtons();", open_handler)

    def test_media_node_resize_completion_keeps_mounted_nodes(self):
        mouseup = source_between(
            "window.onmouseup = e => {",
            "shell.addEventListener('wheel'",
        )
        handler = source_between(
            "    if(resizeState){",
            "    if(llmInstructionResizeState){",
            mouseup,
        )
        self.assertIn("if(changed) syncSelectionUi();", handler)
        self.assertNotIn("if(changed) render();", handler)

    def test_selection_ui_sync_cannot_reset_media(self):
        selection_sync = source_between(
            "function syncSelectionUi(){",
            "function isNodeSelected",
        )
        for forbidden in ("render();", ".innerHTML", ".replaceChildren", ".src =", ".load()"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, selection_sync)


if __name__ == "__main__":
    unittest.main()
