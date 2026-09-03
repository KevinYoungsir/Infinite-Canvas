import asyncio
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


class CanvasLogCleanupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.assets = self.root / "assets"
        self.generated = self.assets / "output"
        self.inputs = self.assets / "input"
        self.legacy = self.root / "output"
        self.data = self.root / "data"
        self.canvases = self.data / "canvases"
        self.conversations = self.data / "conversations"
        self.previews = self.data / "media_previews"
        for path in (self.generated, self.inputs, self.legacy, self.canvases, self.conversations, self.previews):
            path.mkdir(parents=True, exist_ok=True)
        self.history = self.root / "history.json"
        self.global_config = self.root / "global_config.json"
        self.asset_library = self.data / "asset_library.json"
        self.history.write_text("[]", encoding="utf-8")
        self.global_config.write_text("{}", encoding="utf-8")
        self.patches = [
            patch.object(main, "ASSETS_DIR", str(self.assets)),
            patch.object(main, "OUTPUT_OUTPUT_DIR", str(self.generated)),
            patch.object(main, "OUTPUT_INPUT_DIR", str(self.inputs)),
            patch.object(main, "LOCAL_UPLOAD_DIR", str(self.assets / "local")),
            patch.object(main, "OUTPUT_DIR", str(self.legacy)),
            patch.object(main, "DATA_DIR", str(self.data)),
            patch.object(main, "CANVAS_DIR", str(self.canvases)),
            patch.object(main, "CONVERSATION_DIR", str(self.conversations)),
            patch.object(main, "MEDIA_PREVIEW_DIR", str(self.previews)),
            patch.object(main, "HISTORY_FILE", str(self.history)),
            patch.object(main, "GLOBAL_CONFIG_FILE", str(self.global_config)),
            patch.object(main, "ASSET_LIBRARY_PATH", str(self.asset_library)),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def write_canvas(self, canvas_id, logs, nodes=None, updated_at=0):
        value = {
            "id": canvas_id,
            "title": "test",
            "logs": logs,
            "nodes": nodes or [],
            "connections": [],
            "viewport": {"x": 0, "y": 0, "scale": 1},
            "updated_at": updated_at,
        }
        (self.canvases / f"{canvas_id}.json").write_text(json.dumps(value), encoding="utf-8")

    def generated_file(self, name="result.png", content=b"image"):
        path = self.generated / name
        path.write_bytes(content)
        return path, f"/assets/output/{name}"

    def test_collects_nested_local_media_only(self):
        value = {
            "items": [
                {"url": "/assets/output/a.png"},
                "https://example.com/remote.png",
                {"nested": "/output/b.png?x=1"},
            ]
        }
        self.assertEqual(
            main.collect_local_media_urls(value),
            ["/assets/output/a.png", "/output/b.png?x=1"],
        )

    def test_generated_path_rejects_input_files(self):
        generated_path, generated_url = self.generated_file()
        input_path = self.inputs / "reference.png"
        input_path.write_bytes(b"input")
        self.assertEqual(main.generated_media_path_from_url(generated_url), str(generated_path.resolve()))
        self.assertIsNone(main.generated_media_path_from_url("/assets/input/reference.png"))

    def test_output_url_resolves_only_to_output_mount(self):
        generated_collision = self.generated / "same.png"
        legacy_output = self.legacy / "same.png"
        generated_collision.write_bytes(b"generated")
        legacy_output.write_bytes(b"mounted-output")

        self.assertEqual(main.generated_media_path_from_url("/output/same.png"), str(legacy_output.resolve()))

    async def test_record_only_keeps_media(self):
        path, url = self.generated_file()
        self.write_canvas("record_only", [{"id": "log-1", "outputs": [url]}])

        result = await main.delete_canvas_log(
            "record_only",
            main.DeleteCanvasLogRequest(log_id="log-1", delete_unreferenced_media=False),
        )

        self.assertTrue(path.exists())
        self.assertEqual(result["removed_files"], [])
        self.assertEqual(result["canvas"]["logs"], [])

    async def test_cleanup_keeps_media_referenced_by_a_node(self):
        path, url = self.generated_file()
        self.write_canvas(
            "referenced",
            [{"id": "log-1", "outputs": [{"url": url}]}],
            nodes=[{"id": "node-1", "generatedOutputs": [url]}],
        )

        result = await main.delete_canvas_log(
            "referenced",
            main.DeleteCanvasLogRequest(log_id="log-1", delete_unreferenced_media=True),
        )

        self.assertTrue(path.exists())
        self.assertEqual(result["removed_files"], [])
        self.assertEqual(result["skipped_referenced"], [path.name])

    async def test_forced_cleanup_resets_result_node_and_removes_media(self):
        path, url = self.generated_file("node-owned.png")
        self.write_canvas(
            "remove_node",
            [{"id": "log-1", "outputs": [{"url": url}]}],
            nodes=[
                {"id": "prompt", "type": "smart-prompt"},
                {
                    "id": "result",
                    "type": "smart-image",
                    "images": [{"url": url}],
                    "promptDraftText": "keep this prompt",
                    "runInputRefs": [{"url": "/assets/input/reference.png"}],
                    "runSettings": {"model": "test-model"},
                    "runFinishedAt": 999,
                },
            ],
        )
        stored = json.loads((self.canvases / "remove_node.json").read_text(encoding="utf-8"))
        stored["connections"] = [{"id": "edge", "from": "prompt", "to": "result"}]
        (self.canvases / "remove_node.json").write_text(json.dumps(stored), encoding="utf-8")

        result = await main.delete_canvas_log(
            "remove_node",
            main.DeleteCanvasLogRequest(
                log_id="log-1",
                delete_unreferenced_media=True,
                reset_referencing_nodes=True,
            ),
        )

        self.assertFalse(path.exists())
        self.assertEqual([node["id"] for node in result["canvas"]["nodes"]], ["prompt", "result"])
        reset = result["canvas"]["nodes"][1]
        self.assertEqual(reset["images"], [])
        self.assertEqual(reset["pending"], 0)
        self.assertFalse(reset["running"])
        self.assertEqual(reset["promptDraftText"], "keep this prompt")
        self.assertEqual(reset["runInputRefs"], [{"url": "/assets/input/reference.png"}])
        self.assertEqual(reset["runSettings"], {"model": "test-model"})
        self.assertNotIn("runFinishedAt", reset)
        self.assertEqual(result["canvas"]["connections"], [{"id": "edge", "from": "prompt", "to": "result"}])
        self.assertEqual(result["reset_node_ids"], ["result"])

    async def test_forced_cleanup_clears_classic_output_comparison_refs(self):
        path, url = self.generated_file("classic-output.png")
        self.write_canvas(
            "classic_output",
            [{"id": "log-1", "outputs": [url]}],
            nodes=[
                {"id": "generator", "type": "online", "prompt": "keep", "generatedOutputs": [url]},
                {
                    "id": "output",
                    "type": "output",
                    "images": [{"url": url}],
                    "_pending": [{"url": url}],
                    "imageComparisons": {"before": url},
                },
            ],
        )
        stored = json.loads((self.canvases / "classic_output.json").read_text(encoding="utf-8"))
        stored["connections"] = [{"id": "edge", "from": "generator", "to": "output"}]
        (self.canvases / "classic_output.json").write_text(json.dumps(stored), encoding="utf-8")

        result = await main.delete_canvas_log(
            "classic_output",
            main.DeleteCanvasLogRequest(
                log_id="log-1",
                delete_unreferenced_media=True,
                reset_referencing_nodes=True,
            ),
        )

        self.assertFalse(path.exists())
        generator, reset = result["canvas"]["nodes"]
        self.assertEqual(generator["prompt"], "keep")
        self.assertEqual(generator["generatedOutputs"], [])
        self.assertEqual(reset["images"], [])
        self.assertEqual(reset["_pending"], [])
        self.assertEqual(reset["imageComparisons"], {})
        self.assertEqual(result["canvas"]["connections"], [{"id": "edge", "from": "generator", "to": "output"}])

    async def test_reset_clears_all_generated_results_but_keeps_reference_preview(self):
        first, first_url = self.generated_file("first-result.png")
        second, second_url = self.generated_file("second-result.png")
        reference = self.inputs / "reference.png"
        reference.write_bytes(b"reference")
        reference_url = "/assets/input/reference.png"
        self.write_canvas(
            "multi_result",
            [{"id": "log-1", "outputs": [first_url]}],
            nodes=[{
                "id": "result",
                "type": "smart-image",
                "images": [
                    {"url": first_url, "generatedResult": True},
                    {"url": second_url, "generatedResult": True},
                    {"url": reference_url, "loopInputPreview": True},
                ],
                "promptDraftText": "keep prompt",
                "runFinishedAt": 999,
            }],
        )

        result = await main.delete_canvas_log(
            "multi_result",
            main.DeleteCanvasLogRequest(
                log_id="log-1",
                delete_unreferenced_media=True,
                reset_referencing_nodes=True,
            ),
        )

        self.assertFalse(first.exists())
        self.assertFalse(second.exists())
        self.assertTrue(reference.exists())
        reset = result["canvas"]["nodes"][0]
        self.assertEqual(reset["images"], [{"url": reference_url, "loopInputPreview": True}])
        self.assertEqual(reset["promptDraftText"], "keep prompt")
        self.assertNotIn("runFinishedAt", reset)

    async def test_reference_only_downstream_node_does_not_expand_deletion(self):
        source, source_url = self.generated_file("source-result.png")
        downstream, downstream_url = self.generated_file("downstream-result.png")
        self.write_canvas(
            "reference_only",
            [{"id": "log-1", "outputs": [source_url]}],
            nodes=[{
                "id": "downstream",
                "type": "smart-image",
                "images": [
                    {"url": source_url, "loopInputPreview": True},
                    {"url": downstream_url, "generatedResult": True},
                ],
                "runInputRefs": [{"url": source_url}],
                "promptDraftText": "keep downstream",
            }],
        )

        result = await main.delete_canvas_log(
            "reference_only",
            main.DeleteCanvasLogRequest(
                log_id="log-1",
                delete_unreferenced_media=True,
                reset_referencing_nodes=True,
            ),
        )

        self.assertTrue(source.exists())
        self.assertTrue(downstream.exists())
        node = result["canvas"]["nodes"][0]
        self.assertEqual(node["images"], [
            {"url": source_url, "loopInputPreview": True},
            {"url": downstream_url, "generatedResult": True},
        ])
        self.assertEqual(node["promptDraftText"], "keep downstream")
        self.assertEqual(result["reset_node_ids"], [])

    async def test_cleanup_deletes_unreferenced_media_and_preview(self):
        path, url = self.generated_file()
        preview = Path(main.media_preview_cache_paths(str(path), 256)[0])
        preview.write_bytes(b"preview")
        self.write_canvas("unreferenced", [{"id": "log-1", "outputs": [url]}])

        result = await main.delete_canvas_log(
            "unreferenced",
            main.DeleteCanvasLogRequest(log_id="log-1", delete_unreferenced_media=True),
        )

        self.assertFalse(path.exists())
        self.assertFalse(preview.exists())
        self.assertEqual(result["removed_files"], [path.name])
        self.assertEqual(result["removed_previews"], 1)

    async def test_generation_history_does_not_pin_deleted_log_media(self):
        path, url = self.generated_file("history-only.png")
        self.history.write_text(
            json.dumps([{"timestamp": 123, "url": url, "images": [url]}]),
            encoding="utf-8",
        )
        self.write_canvas("history_only", [{"id": "log-1", "outputs": [url]}])

        result = await main.delete_canvas_log(
            "history_only",
            main.DeleteCanvasLogRequest(log_id="log-1", delete_unreferenced_media=True),
        )

        self.assertFalse(path.exists())
        self.assertEqual(result["removed_files"], [path.name])
        self.assertEqual(json.loads(self.history.read_text(encoding="utf-8")), [])

    async def test_cleanup_preserves_media_when_json_is_unreadable(self):
        path, url = self.generated_file()
        (self.canvases / "being-written.json").write_text("{", encoding="utf-8")
        self.write_canvas("unreadable_owner", [{"id": "log-1", "outputs": [url]}])

        result = await main.delete_canvas_log(
            "unreadable_owner",
            main.DeleteCanvasLogRequest(log_id="log-1", delete_unreferenced_media=True),
        )

        self.assertTrue(path.exists())
        self.assertEqual(result["skipped_referenced"], [path.name])

    async def test_stale_delete_is_rejected_without_changing_canvas(self):
        path, url = self.generated_file()
        self.write_canvas("stale", [{"id": "log-1", "outputs": [url]}], updated_at=200)

        with self.assertRaises(main.HTTPException) as caught:
            await main.delete_canvas_log(
                "stale",
                main.DeleteCanvasLogRequest(
                    log_id="log-1",
                    delete_unreferenced_media=True,
                    base_updated_at=100,
                ),
            )

        self.assertEqual(caught.exception.status_code, 409)
        self.assertTrue(path.exists())
        stored = json.loads((self.canvases / "stale.json").read_text(encoding="utf-8"))
        self.assertEqual([item["id"] for item in stored["logs"]], ["log-1"])

    async def test_saved_version_advances_when_clock_is_unchanged(self):
        _, url = self.generated_file()
        self.write_canvas("monotonic", [{"id": "log-1", "outputs": [url]}], updated_at=200)

        with patch.object(main, "now_ms", return_value=200):
            result = await main.delete_canvas_log(
                "monotonic",
                main.DeleteCanvasLogRequest(log_id="log-1", base_updated_at=200),
            )

        self.assertEqual(result["canvas"]["updated_at"], 201)

    def test_generated_paths_reject_unsafe_urls(self):
        path, url = self.generated_file()
        outside = self.root / "outside.png"
        outside.write_bytes(b"outside")
        urls = [
            "/assets/output/../../outside.png", "/assets/output/../output/result.png",
            "/assets/output/%2e%2e/%2e%2e/outside.png", "/assets/output/..%5c..%5coutside.png",
            "/assets/output//result.png", "/assets/output/./result.png",
            "/assets/output/C:/outside.png", "/assets/output/result.png:stream",
            "/assets/output/result.png%00", "/assets/output/result.png.",
            "/assets/output/result.png%20", "/assets/output/%ff.png",
            "https://example.com" + url, "http://127.0.0.1:3000" + url,
            "//example.com" + url, "file:///" + str(path), str(path),
            "/api/storage-files/generated/../outside.png",
            "/api/storage-files/unknown/result.png", "\n" + url,
        ]
        for candidate in urls:
            with self.subTest(url=candidate):
                self.assertIsNone(main.generated_media_path_from_url(candidate))
        self.assertEqual(outside.read_bytes(), b"outside")
        self.assertTrue(path.exists())

    def test_generated_paths_respect_mounts_and_custom_storage(self):
        custom = self.root / "custom-generated"
        custom.mkdir()
        result = custom / "result name.png"
        result.write_bytes(b"generated")
        input_path = self.inputs / "result.png"
        input_path.write_bytes(b"reference")
        with patch.object(main, "OUTPUT_OUTPUT_DIR", str(custom)):
            self.assertEqual(main.generated_media_path_from_url(
                "/api/storage-files/generated/result%20name.png?download=1#preview"
            ), str(result.resolve()))
            self.assertIsNone(main.generated_media_path_from_url("/api/storage-files/upload/result.png"))
            self.assertIsNone(main.generated_media_path_from_url("/output/result%20name.png"))
        library = self.assets / "library"
        library.mkdir()
        (library / "keep.png").write_bytes(b"library")
        self.assertIsNone(main.generated_media_path_from_url("/assets/library/keep.png"))

    def test_output_mount_has_no_fallback_and_missing_files_are_ignored(self):
        self.generated_file("only-generated.png")
        self.assertIsNone(main.generated_media_path_from_url("/output/only-generated.png"))
        self.assertIsNone(main.generated_media_path_from_url("/assets/output/missing.png"))
        self.assertIsNone(main.generated_media_path_from_url("/assets/output/"))

    def make_directory_alias(self, alias, target):
        # Both paths are disposable test fixtures. Junctions do not require the
        # Windows privilege needed for symbolic links; neither branch skips QA.
        self.assertTrue(alias.is_relative_to(self.root))
        self.assertTrue(target.is_relative_to(self.root))
        try:
            alias.symlink_to(target, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                raise
            subprocess.run(["cmd", "/c", "mklink", "/J", str(alias), str(target)],
                           check=True, capture_output=True)

    def test_generated_paths_reject_directory_links_inside_and_outside_root(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "keep.png").write_bytes(b"outside")
        self.make_directory_alias(self.generated / "escape", outside)
        self.make_directory_alias(self.generated / "alias", self.inputs)
        (self.inputs / "keep.png").write_bytes(b"input")
        nested = self.generated / "nested"
        nested.mkdir()
        (nested / "keep.png").write_bytes(b"generated")
        self.make_directory_alias(self.generated / "inside", nested)
        for folder in ("escape", "alias", "inside"):
            with self.subTest(folder=folder):
                self.assertIsNone(main.generated_media_path_from_url(f"/assets/output/{folder}/keep.png"))

    async def test_cleanup_preserves_shared_document_owners(self):
        owners = ("canvas", "trash", "conversation", "asset", "config", "other-log")
        for owner in owners:
            with self.subTest(owner=owner):
                path, url = self.generated_file(f"shared-{owner}.png")
                self.write_canvas(owner, [{"id": "delete", "outputs": [url]}])
                reference = {"nested": [{"url": url + "?w=256#preview"}]}
                if owner in {"canvas", "trash"}:
                    reference["deleted_at"] = 123 if owner == "trash" else 0
                    destination = self.canvases / f"other-{owner}.json"
                elif owner == "conversation":
                    destination = self.conversations / "user" / "conversation.json"
                    destination.parent.mkdir()
                elif owner == "asset":
                    destination = self.asset_library
                elif owner == "config":
                    destination = self.global_config
                else:
                    self.write_canvas(owner, [{"id": "delete", "outputs": [url]},
                                              {"id": "keep", "outputs": [url]}])
                    destination = None
                if destination:
                    destination.write_text(json.dumps(reference), encoding="utf-8")
                result = await main.delete_canvas_log(owner, main.DeleteCanvasLogRequest(
                    log_id="delete", delete_unreferenced_media=True, reset_referencing_nodes=True))
                self.assertTrue(path.exists())
                self.assertEqual(result["removed_files"], [])
                self.assertEqual(result["skipped_referenced"], [path.name])

    async def test_cleanup_counts_link_aliases_as_shared_references(self):
        path, url = self.generated_file("aliased.png")
        self.make_directory_alias(self.inputs / "alias", self.generated)
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
        self.write_canvas("consumer", [], nodes=[{"url": "/assets/input/alias/aliased.png"}])
        result = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
            log_id="log-1", delete_unreferenced_media=True))
        self.assertTrue(path.exists())
        self.assertEqual(result["skipped_referenced"], [path.name])

    async def test_cleanup_preserves_files_when_reference_scan_fails(self):
        path, url = self.generated_file()
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
        with patch.object(main.os, "walk", side_effect=PermissionError("scan denied")):
            result = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
                log_id="log-1", delete_unreferenced_media=True))
        self.assertTrue(path.exists())
        self.assertEqual(result["skipped_referenced"], [path.name])

    async def test_cleanup_rechecks_path_after_reference_scan(self):
        path, url = self.generated_file()
        canonical = str(path.resolve())
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
        original = main.cleanup_media_file_path
        scanned = False

        def scan(_path):
            nonlocal scanned
            scanned = True
            return False

        def resolve(*args, **kwargs):
            result = original(*args, **kwargs)
            return None if scanned and result == canonical else result

        with (patch.object(main, "persisted_json_references_media_path", side_effect=scan),
              patch.object(main, "cleanup_media_file_path", side_effect=resolve)):
            result = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
                log_id="log-1", delete_unreferenced_media=True))
        self.assertTrue(path.exists())
        self.assertFalse(result["ok"])
        self.assertEqual(result["removed_files"], [])
        self.assertTrue(result["cleanup_errors"])

    async def test_cleanup_reports_unlink_failure_and_keeps_history(self):
        path, url = self.generated_file()
        self.history.write_text(json.dumps([{"url": url}]), encoding="utf-8")
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
        with patch.object(main.os, "remove", side_effect=PermissionError("unlink denied")):
            result = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
                log_id="log-1", delete_unreferenced_media=True))
        self.assertTrue(path.exists())
        self.assertFalse(result["ok"])
        self.assertEqual(result["removed_files"], [])
        self.assertIn("unlink denied", result["cleanup_errors"][0]["error"])
        self.assertEqual(json.loads(self.history.read_text(encoding="utf-8")), [{"url": url}])

    async def test_cleanup_never_unlinks_if_canvas_save_fails(self):
        path, url = self.generated_file()
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
        before = (self.canvases / "owner.json").read_bytes()
        with (patch.object(main, "save_canvas", side_effect=OSError("save failed")),
              patch.object(main.os, "remove") as remove):
            with self.assertRaisesRegex(OSError, "save failed"):
                await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
                    log_id="log-1", delete_unreferenced_media=True))
            remove.assert_not_called()
        self.assertTrue(path.exists())
        self.assertEqual((self.canvases / "owner.json").read_bytes(), before)

    async def test_cleanup_ignores_missing_remote_and_input_outputs(self):
        reference = self.inputs / "reference.png"
        reference.write_bytes(b"keep")
        self.write_canvas("owner", [{"id": "log-1", "outputs": [
            "/assets/input/reference.png", "/assets/output/missing.png",
            "https://example.com/remote.png",
        ]}])
        result = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
            log_id="log-1", delete_unreferenced_media=True))
        self.assertTrue(result["ok"])
        self.assertTrue(reference.exists())
        self.assertEqual(result["removed_files"], [])

    async def test_cleanup_removes_all_matching_previews_only(self):
        path, url = self.generated_file()
        other, _ = self.generated_file("other.png")
        expected = []
        for width in (64, 256, 512, 2048):
            for cache in main.media_preview_cache_paths(str(path), width):
                Path(cache).write_bytes(b"preview")
                expected.append(Path(cache))
        stat = path.stat()
        key = main.hashlib.sha1(f"{path}|{stat.st_mtime_ns}|{stat.st_size}|0|jpg".encode()).hexdigest()
        jpg = self.previews / f"{key}.jpg"
        jpg.write_bytes(b"jpeg")
        expected.append(jpg)
        kept = Path(main.media_preview_cache_paths(str(other), 256)[0])
        kept.write_bytes(b"keep")
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
        result = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
            log_id="log-1", delete_unreferenced_media=True))
        self.assertEqual(result["removed_previews"], len(expected))
        self.assertTrue(all(not cache.exists() for cache in expected))
        self.assertTrue(kept.exists())
        self.assertTrue(other.exists())

    async def test_missing_log_and_invalid_id_do_not_change_data(self):
        path, url = self.generated_file()
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
        before = (self.canvases / "owner.json").read_bytes()
        for canvas_id, log_id, status in (("owner", "missing", 404), ("owner", " ", 400),
                                           ("../owner", "log-1", 400)):
            with self.subTest(canvas_id=canvas_id, log_id=log_id):
                with self.assertRaises(main.HTTPException) as caught:
                    await main.delete_canvas_log(canvas_id, main.DeleteCanvasLogRequest(
                        log_id=log_id, delete_unreferenced_media=True))
                self.assertEqual(caught.exception.status_code, status)
        self.assertTrue(path.exists())
        self.assertEqual((self.canvases / "owner.json").read_bytes(), before)

    async def test_http_log_delete_route_is_registered_and_validates_payload(self):
        _, url = self.generated_file()
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
        async with main.httpx.AsyncClient(transport=main.httpx.ASGITransport(app=main.app),
                                         base_url="http://test") as client:
            invalid = await client.post("/api/canvases/owner/logs/delete", json={})
            self.assertEqual(invalid.status_code, 422)
            response = await client.post("/api/canvases/owner/logs/delete", json={"log_id": "log-1"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["canvas"]["logs"], [])

    async def test_concurrent_stale_save_cannot_restore_deleted_log(self):
        _, url = self.generated_file()
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}], updated_at=200)
        entered, release = threading.Event(), threading.Event()
        original_scan = main.persisted_json_references_media_path

        def paused_scan(path):
            entered.set()
            if not release.wait(5):
                raise TimeoutError("concurrent test was not released")
            return original_scan(path)

        payload = main.CanvasSaveRequest(base_updated_at=200, logs=[{"id": "log-1", "outputs": [url]}])
        with patch.object(main, "persisted_json_references_media_path", side_effect=paused_scan):
            deletion = asyncio.create_task(main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
                log_id="log-1", base_updated_at=200, delete_unreferenced_media=True)))
            try:
                self.assertTrue(await asyncio.to_thread(entered.wait, 5))
                update = asyncio.create_task(asyncio.to_thread(
                    lambda: asyncio.run(main.update_canvas("owner", payload))))
            finally:
                release.set()
            await deletion
            with self.assertRaises(main.HTTPException) as caught:
                await update
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(main.load_canvas("owner")["logs"], [])

    async def test_normalized_reference_url_still_protects_media(self):
        path, url = self.generated_file()
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
        self.write_canvas("consumer", [], nodes=[{"url": "/assets/input/../output/result.png"}])
        result = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
            log_id="log-1", delete_unreferenced_media=True))
        self.assertTrue(path.exists())
        self.assertEqual(result["skipped_referenced"], [path.name])

    async def test_unrelated_nested_documents_do_not_pin_media(self):
        path, url = self.generated_file()
        user = self.conversations / "user"
        user.mkdir()
        (user / "chat.json").write_text('{"messages": []}', encoding="utf-8")
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
        result = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
            log_id="log-1", delete_unreferenced_media=True))
        self.assertFalse(path.exists())
        self.assertEqual(result["removed_files"], [path.name])

    async def test_unscanned_document_directory_link_preserves_media(self):
        path, url = self.generated_file()
        outside = self.root / "linked-documents"
        outside.mkdir()
        (outside / "chat.json").write_text(json.dumps({"url": url}), encoding="utf-8")
        self.make_directory_alias(self.conversations / "linked-user", outside)
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
        result = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
            log_id="log-1", delete_unreferenced_media=True))
        self.assertTrue(path.exists())
        self.assertEqual(result["skipped_referenced"], [path.name])

    async def test_path_change_during_preview_cleanup_cannot_unlink_source(self):
        path, url = self.generated_file()
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
        original = main.generated_media_file_path
        preview_done = False

        def previews(_path):
            nonlocal preview_done
            preview_done = True
            return 0

        def resolve(candidate):
            return None if preview_done else original(candidate)

        with (patch.object(main, "delete_media_preview_cache", side_effect=previews),
              patch.object(main, "generated_media_file_path", side_effect=resolve)):
            result = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
                log_id="log-1", delete_unreferenced_media=True))
        self.assertTrue(path.exists())
        self.assertFalse(result["ok"])
        self.assertEqual(result["removed_files"], [])

    async def test_atomic_canvas_save_failure_keeps_original_document_and_media(self):
        path, url = self.generated_file()
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
        before = (self.canvases / "owner.json").read_bytes()
        with patch.object(main.os, "replace", side_effect=PermissionError("replace denied")):
            with self.assertRaisesRegex(PermissionError, "replace denied"):
                await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
                    log_id="log-1", delete_unreferenced_media=True))
        self.assertTrue(path.exists())
        self.assertEqual((self.canvases / "owner.json").read_bytes(), before)
        self.assertEqual(list(self.canvases.glob(".json-*.tmp")), [])

    async def test_history_failure_is_reported_without_truncating_index(self):
        path, url = self.generated_file()
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
        self.history.write_text(json.dumps([{"url": url}]), encoding="utf-8")
        before = self.history.read_bytes()
        replace = main.os.replace

        def replace_except_history(source, destination):
            if os.path.normcase(os.path.abspath(destination)) == os.path.normcase(str(self.history.absolute())):
                raise PermissionError("history replace denied")
            return replace(source, destination)

        with patch.object(main.os, "replace", side_effect=replace_except_history):
            result = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
                log_id="log-1", delete_unreferenced_media=True))
        self.assertFalse(path.exists())
        self.assertFalse(result["ok"])
        self.assertEqual(result["removed_files"], [path.name])
        self.assertEqual(result["cleanup_errors"][0]["file"], "generation history")
        self.assertEqual(self.history.read_bytes(), before)

    async def test_canvas_writers_lock_before_reading_snapshot(self):
        self.write_canvas("owner", [], updated_at=200)
        lock_depth = 0
        original_load, original_load_any = main.load_canvas, main.load_canvas_any

        class RecordingLock:
            def __enter__(self):
                nonlocal lock_depth
                lock_depth += 1

            def __exit__(self, *_args):
                nonlocal lock_depth
                lock_depth -= 1

        def checked_load(canvas_id):
            self.assertGreater(lock_depth, 0, "read must be inside the mutation lock")
            return original_load(canvas_id)

        def checked_load_any(canvas_id):
            self.assertGreater(lock_depth, 0, "read must be inside the mutation lock")
            return original_load_any(canvas_id)

        with (patch.object(main, "CANVAS_LOCK", RecordingLock()),
              patch.object(main, "load_canvas", side_effect=checked_load),
              patch.object(main, "load_canvas_any", side_effect=checked_load_any)):
            await main.update_canvas_meta("owner", main.CanvasMetaUpdate(title="renamed"))
            self.assertEqual(original_load("owner")["updated_at"], 200)
            await main.touch_canvas("owner")
            await main.delete_canvas("owner")
            await main.restore_canvas("owner")
            await main.update_canvas("owner", main.CanvasSaveRequest(title="saved"))
        self.assertEqual(main.load_canvas("owner")["title"], "saved")

    def test_rejects_malformed_percent_encoding_even_if_literal_file_exists(self):
        for name in ("bad%.png", "bad%2.png", "bad%GG.png", "bad%0G.png"):
            with self.subTest(name=name):
                path = self.legacy / name
                path.write_bytes(b"keep")
                self.assertIsNone(main.generated_media_path_from_url("/output/" + name))
                encoded = main.urllib.parse.quote(name)
                self.assertEqual(main.generated_media_path_from_url("/output/" + encoded), str(path.resolve()))
                self.assertTrue(path.exists())

    async def test_reference_stat_errors_fail_closed(self):
        self.asset_library.write_text("{}", encoding="utf-8")
        for location in (self.conversations, self.asset_library):
            with self.subTest(location=location.name):
                path, url = self.generated_file()
                self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
                denied = os.path.normcase(str(location.resolve()))
                original_stat = os.stat

                def guarded_stat(candidate, *args, **kwargs):
                    if os.path.normcase(os.path.realpath(candidate)) == denied:
                        raise PermissionError("reference stat denied")
                    return original_stat(candidate, *args, **kwargs)

                with patch.object(main.os, "stat", side_effect=guarded_stat):
                    result = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
                        log_id="log-1", delete_unreferenced_media=True))
                self.assertTrue(path.exists())
                self.assertEqual(result["removed_files"], [])
                self.assertEqual(result["skipped_referenced"], [path.name])

    async def test_deep_reference_document_fails_closed(self):
        path, url = self.generated_file()
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
        (self.canvases / "deep.json").write_text("[" * 2000 + "0" + "]" * 2000, encoding="utf-8")
        result = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
            log_id="log-1", delete_unreferenced_media=True))
        self.assertTrue(path.exists())
        self.assertEqual(result["skipped_referenced"], [path.name])

    def test_output_path_security_matrix_and_single_decoding(self):
        outside = self.root / "outside.png"
        outside.write_bytes(b"outside")
        mounted = self.legacy / "a.png"
        mounted.write_bytes(b"mounted")
        unsafe = [
            "../outside.png", "..\\outside.png", "/absolute/path", r"C:\Windows\outside.png",
            "C:/Windows/outside.png", r"\\server\share\outside.png", "file:///outside.png",
            "http://example.com/output/a.png", "https://example.com/output/a.png",
            "/output/../outside.png", "/output/..\\outside.png",
            "/output/%2e%2e/outside.png", "/output/%2E%2E/outside.png",
            "/output/%252e%252e/outside.png", "/outputevil/a.png",
            "/output/%2Fabsolute/path", "/output/%5C%5Cserver%5Cshare",
            "/output/C:/Windows/outside.png", "/output/missing.png",
        ]
        for url in unsafe:
            with self.subTest(url=url):
                self.assertIsNone(main.generated_media_path_from_url(url))
        for suffix in ("?x=1", "#test", "?x=%GG#test"):
            with self.subTest(suffix=suffix):
                self.assertEqual(main.generated_media_path_from_url("/output/a.png" + suffix),
                                 str(mounted.resolve()))
        literal_directory = self.legacy / "%2e%2e"
        literal_directory.mkdir()
        literal = literal_directory / "outside.png"
        literal.write_bytes(b"literal percent name, not parent directory")
        self.assertEqual(main.generated_media_path_from_url("/output/%252e%252e/outside.png"),
                         str(literal.resolve()))
        self.assertEqual(outside.read_bytes(), b"outside")

    async def test_http_default_deletes_only_log_without_media_opt_in(self):
        path, url = self.generated_file()
        node = {"id": "result", "type": "smart-image", "images": [{"url": url}]}
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}], nodes=[node])
        preview = Path(main.media_preview_cache_paths(str(path), 256)[0])
        preview.write_bytes(b"preview")
        self.history.write_text(json.dumps([{"url": url}]), encoding="utf-8")
        async with main.httpx.AsyncClient(transport=main.httpx.ASGITransport(app=main.app),
                                         base_url="http://test") as client:
            response = await client.post("/api/canvases/owner/logs/delete", json={"log_id": "log-1"})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["ok"])
        self.assertEqual(result["canvas"]["logs"], [])
        self.assertEqual(result["canvas"]["nodes"], [node])
        self.assertEqual(result["removed_files"], [])
        self.assertEqual(result["removed_previews"], 0)
        self.assertEqual(result["reset_node_ids"], [])
        self.assertEqual(path.read_bytes(), b"image")
        self.assertEqual(preview.read_bytes(), b"preview")
        self.assertEqual(json.loads(self.history.read_text(encoding="utf-8")), [{"url": url}])

    async def test_two_nodes_sharing_media_survive_log_cleanup(self):
        path, url = self.generated_file()
        nodes = [{"id": name, "type": "smart-image", "images": [{"url": url}]}
                 for name in ("node-a", "node-b")]
        self.write_canvas("owner", [{"id": "log-a", "nodeId": "node-a", "outputs": [url]}], nodes=nodes)
        result = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
            log_id="log-a", delete_unreferenced_media=True))
        self.assertTrue(path.exists())
        self.assertEqual(result["canvas"]["nodes"], nodes)
        self.assertEqual(result["canvas"]["logs"], [])
        self.assertEqual(result["skipped_referenced"], [path.name])

    async def test_cleanup_cannot_delete_through_directory_link(self):
        outside = self.root / "outside-generated"
        outside.mkdir()
        sentinel = outside / "keep.png"
        sentinel.write_bytes(b"outside allowed roots")
        self.make_directory_alias(self.generated / "escape", outside)
        self.write_canvas("owner", [{"id": "log-1", "outputs": ["/assets/output/escape/keep.png"]}])
        result = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
            log_id="log-1", delete_unreferenced_media=True))
        self.assertEqual(result["removed_files"], [])
        self.assertEqual(sentinel.read_bytes(), b"outside allowed roots")

    async def test_cleanup_structural_diff_preserves_non_result_canvas_data(self):
        path, url = self.generated_file()
        reference = {"url": "/assets/input/reference.png", "loopInputPreview": True}
        nodes = [
            {"id": "prompt", "type": "smart-prompt", "text": "keep prompt", "x": 10, "y": 20},
            {"id": "result", "type": "smart-image", "x": 30, "y": 40,
             "images": [reference, {"url": url, "generatedResult": True}],
             "generatedOutputs": [url], "promptDraftText": "keep draft",
             "runInputRefs": [{"url": "/assets/input/reference.png"}],
             "runSettings": {"model": "existing-model", "seed": 17},
             "pending": 1, "running": True, "queued": True, "runFinishedAt": 99},
            {"id": "group", "type": "smart-group", "items": ["prompt", "result"], "x": 50, "y": 60},
        ]
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}, {"id": "keep-log"}],
                          nodes=nodes, updated_at=200)
        before = main.load_canvas("owner")
        before["connections"] = [{"id": "edge", "from": "prompt", "to": "result"}]
        before["settings"] = {"quality": "high"}
        (self.canvases / "owner.json").write_text(json.dumps(before), encoding="utf-8")
        expected = json.loads(json.dumps(before))
        expected["logs"] = [{"id": "keep-log"}]
        expected["updated_at"] = 201
        expected_node = expected["nodes"][1]
        expected_node.update(images=[reference], generatedOutputs=[], pending=0, running=False, queued=False)
        expected_node.pop("runFinishedAt")
        with patch.object(main, "now_ms", return_value=200):
            result = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
                log_id="log-1", delete_unreferenced_media=True, reset_referencing_nodes=True,
                base_updated_at=200))
        self.assertEqual(result["canvas"], expected)
        self.assertEqual(main.load_canvas("owner"), expected)
        self.assertEqual(result["reset_node_ids"], ["result"])
        self.assertFalse(path.exists())

    def test_atomic_json_write_failure_preserves_original_and_cleans_same_directory_temp(self):
        target = self.canvases / "owner.json"
        target.write_text('{"original": true}', encoding="utf-8")
        before = target.read_bytes()
        mkstemp = main.tempfile.mkstemp

        def checked_temp(*args, **kwargs):
            self.assertEqual(Path(kwargs["dir"]).resolve(), target.parent.resolve())
            return mkstemp(*args, **kwargs)

        def failed_dump(_value, handle, **_kwargs):
            handle.write('{"incomplete":')
            raise OSError("write failed")

        with (patch.object(main.tempfile, "mkstemp", side_effect=checked_temp) as create_temp,
              patch.object(main.json, "dump", side_effect=failed_dump)):
            with self.assertRaisesRegex(OSError, "write failed"):
                main.write_json_atomic(str(target), {"replacement": True})
            create_temp.assert_called_once()
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(list(target.parent.glob(".json-*.tmp")), [])
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"original": True})

    async def test_sequential_cleanup_versions_increase_with_frozen_clock(self):
        first, first_url = self.generated_file("first.png")
        second, second_url = self.generated_file("second.png")
        urls = [first_url, second_url]
        self.write_canvas("owner", [{"id": str(index), "outputs": [url]} for index, url in enumerate(urls)],
                          updated_at=200)
        self.history.write_text(json.dumps([{"url": url} for url in urls]), encoding="utf-8")
        previews = [Path(main.media_preview_cache_paths(str(path), 256)[0]) for path in (first, second)]
        for preview in previews:
            preview.write_bytes(b"preview")
        with patch.object(main, "now_ms", return_value=200):
            one = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
                log_id="0", delete_unreferenced_media=True, base_updated_at=200))
            two = await main.delete_canvas_log("owner", main.DeleteCanvasLogRequest(
                log_id="1", delete_unreferenced_media=True, base_updated_at=201))
        self.assertEqual(one["canvas"]["updated_at"], 201)
        self.assertEqual(two["canvas"]["updated_at"], 202)
        self.assertTrue(one["ok"] and two["ok"])
        self.assertEqual((one["removed_previews"], two["removed_previews"]), (1, 1))
        self.assertEqual(main.load_canvas("owner")["updated_at"], 202)
        self.assertEqual(json.loads(self.history.read_text(encoding="utf-8")), [])
        self.assertTrue(all(not path.exists() for path in [first, second, *previews]))

    async def test_http_partial_history_failure_reports_applied_mutations(self):
        path, url = self.generated_file()
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
        self.history.write_text(json.dumps([{"url": url}]), encoding="utf-8")
        before = self.history.read_bytes()
        replace = main.os.replace

        def replace_except_history(source, destination):
            if Path(destination).resolve() == self.history.resolve():
                raise PermissionError("history replace denied")
            return replace(source, destination)

        async with main.httpx.AsyncClient(transport=main.httpx.ASGITransport(app=main.app),
                                         base_url="http://test") as client:
            with patch.object(main.os, "replace", side_effect=replace_except_history):
                response = await client.post("/api/canvases/owner/logs/delete", json={
                    "log_id": "log-1", "delete_unreferenced_media": True})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result["ok"])
        self.assertEqual(result["removed_files"], [path.name])
        self.assertEqual(result["canvas"]["logs"], [])
        self.assertEqual(main.load_canvas("owner")["logs"], [])
        self.assertIn("history replace denied", result["cleanup_errors"][0]["error"])
        self.assertEqual(result["cleanup_errors"][0]["file"], "generation history")
        self.assertFalse(path.exists())
        self.assertEqual(self.history.read_bytes(), before)
        self.assertEqual(list(self.root.glob(".json-*.tmp")), [])

    async def test_history_read_failures_report_already_applied_cleanup(self):
        for failure in ("permission", "deep-json"):
            with self.subTest(failure=failure):
                path, url = self.generated_file()
                self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}])
                history_text = "[" * 2000 + "0" + "]" * 2000 if failure == "deep-json" else json.dumps([{"url": url}])
                self.history.write_text(history_text, encoding="utf-8")
                before = self.history.read_bytes()
                original_open = open

                def guarded_open(filename, *args, **kwargs):
                    if failure == "permission" and Path(filename).resolve() == self.history.resolve():
                        raise PermissionError("history read denied")
                    return original_open(filename, *args, **kwargs)

                async with main.httpx.AsyncClient(transport=main.httpx.ASGITransport(app=main.app),
                                                 base_url="http://test") as client:
                    with patch("builtins.open", side_effect=guarded_open):
                        response = await client.post("/api/canvases/owner/logs/delete", json={
                            "log_id": "log-1", "delete_unreferenced_media": True})
                self.assertEqual(response.status_code, 200)
                result = response.json()
                self.assertFalse(result["ok"])
                self.assertEqual(result["removed_files"], [path.name])
                self.assertEqual(result["canvas"]["logs"], [])
                self.assertEqual(result["cleanup_errors"][0]["file"], "generation history")
                self.assertEqual(self.history.read_bytes(), before)
                self.assertFalse(path.exists())

    async def test_http_repeated_delete_is_stable_not_found_without_further_mutation(self):
        path, url = self.generated_file()
        other, _ = self.generated_file("keep.png")
        self.write_canvas("owner", [{"id": "log-1", "outputs": [url]}, {"id": "keep-log"}])
        payload = {"log_id": "log-1", "delete_unreferenced_media": True}
        async with main.httpx.AsyncClient(transport=main.httpx.ASGITransport(app=main.app),
                                         base_url="http://test") as client:
            first = await client.post("/api/canvases/owner/logs/delete", json=payload)
            saved = (self.canvases / "owner.json").read_bytes()
            second = await client.post("/api/canvases/owner/logs/delete", json=payload)
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["ok"])
        self.assertEqual(second.status_code, 404)
        self.assertEqual((self.canvases / "owner.json").read_bytes(), saved)
        self.assertEqual(main.load_canvas("owner")["logs"], [{"id": "keep-log"}])
        self.assertFalse(path.exists())
        self.assertEqual(other.read_bytes(), b"image")

    async def test_save_preserves_smart_canvas_nodes_membership_order_and_connections(self):
        nodes = [
            {"id": "group", "type": "smart-group", "items": ["b", "a"], "images": []},
            {"id": "a", "type": "smart-image", "images": [{"url": "/assets/input/a.png"}], "x": 12, "y": 34},
            {"id": "b", "type": "smart-image", "images": [{"url": "/assets/input/d.png"}, {"url": "/assets/input/c.png"}]},
            {"id": "blank", "type": "smart-image", "images": [], "x": 100, "y": 200},
        ]
        connections = [{"id": "edge", "from": "a", "to": "blank", "kind": "input"}]
        self.write_canvas("owner", [], nodes=nodes, updated_at=200)
        stored = main.load_canvas("owner")
        stored["kind"] = "smart"
        (self.canvases / "owner.json").write_text(json.dumps(stored), encoding="utf-8")
        result = await main.update_canvas("owner", main.CanvasSaveRequest(
            nodes=nodes, connections=connections, viewport={"x": 30, "y": 40, "scale": 0.75}, base_updated_at=200))
        persisted = main.load_canvas("owner")
        self.assertEqual(persisted["nodes"], nodes)
        self.assertEqual(persisted["connections"], connections)
        self.assertEqual(persisted["viewport"], {"x": 30, "y": 40, "scale": 0.75})
        self.assertEqual(persisted, result["canvas"])


if __name__ == "__main__":
    unittest.main()
