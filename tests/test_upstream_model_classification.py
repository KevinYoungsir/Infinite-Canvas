import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


class UpstreamModelClassificationTests(unittest.TestCase):
    def test_seedance_variants_are_video_models(self):
        for model_id in (
            "seedance-1-5-pro",
            "seedance-2.0",
            "seedance-2.0-fast-face",
            "seedance-2.5",
            "doubao-seedance-2-0-260128",
        ):
            with self.subTest(model_id=model_id):
                self.assertEqual(main.classify_upstream_model(model_id), "video")

    def test_upstream_seedance_is_grouped_as_video(self):
        grouped, ids = main.parse_upstream_models({
            "data": [
                {"id": "gpt-5.5"},
                {"id": "seedance-2.5"},
                {"id": "seedance-2.0-fast"},
                {"id": '["doubao-seedance-1-0-pro-quality"]'},
            ]
        }, "apimart")

        self.assertEqual(ids, [
            "doubao-seedance-1-0-pro-quality",
            "gpt-5.5",
            "seedance-2.0-fast",
            "seedance-2.5",
        ])
        self.assertEqual(grouped["chat"], ["gpt-5.5"])
        self.assertEqual(grouped["video"], [
            "doubao-seedance-1-0-pro-quality",
            "seedance-2.0-fast",
            "seedance-2.5",
        ])

    def test_saved_models_are_migrated_to_their_canvas_categories(self):
        provider = main.normalize_provider({
            "id": "apimart",
            "name": "APIMART",
            "base_url": "https://api.apimart.ai",
            "protocol": "apimart",
            "image_models": ["seedance-1-5-pro", "gpt-image-2", "midjourney"],
            "chat_models": ["seedance-2.0", "gpt-5.5"],
            "video_models": ["seedance-2.5"],
        })

        self.assertEqual(provider["image_models"], ["gpt-image-2", "midjourney"])
        self.assertEqual(provider["chat_models"], ["gpt-5.5"])
        self.assertEqual(
            provider["video_models"],
            ["seedance-2.5", "seedance-1-5-pro", "seedance-2.0"],
        )

    def test_midjourney_channel_failure_is_retryable(self):
        raw = {
            "error": {
                "message": "Please wait and try again later. Thank you for your patience!",
                "type": "apimart_error",
                "code": "get_channel_failed",
            }
        }
        self.assertTrue(main.midjourney_retryable_submission(400, raw))

    def test_pulled_midjourney_model_is_classified_as_image(self):
        grouped, ids = main.parse_upstream_models(
            {"data": [{"id": "midjourney"}, {"id": "gpt-5.5"}]},
            "apimart",
        )

        self.assertEqual(ids, ["gpt-5.5", "midjourney"])
        self.assertEqual(grouped["image"], ["midjourney"])
        self.assertEqual(grouped["chat"], ["gpt-5.5"])

    def test_apimart_visual_model_families_use_documented_categories(self):
        expected = {
            "MiniMax-H3": "video",
            "MiniMax-H3-Context-IR": "video",
            "MiniMax-H3-Regeneration": "video",
            "Omni-Flash-Ext": "video",
            "gemini-omni-flash-preview": "video",
            "happyhorse-1.1": "video",
            "pixverse-v6": "video",
            "skyreels-v4-fast": "video",
            "viduq3-pro": "video",
            "grok-imagine-1.5-apimart": "image",
            "grok-imagine-2.0-ext": "image",
            "wan2.7-image": "image",
            "wan2.7-image-pro": "image",
            "text-moderation-stable": "chat",
        }
        for model_id, category in expected.items():
            with self.subTest(model_id=model_id):
                self.assertEqual(main.classify_upstream_model(model_id, "apimart"), category)

    def test_apimart_h3_is_pulled_into_video_not_chat(self):
        grouped, ids = main.parse_upstream_models({
            "data": [
                {"id": "MiniMax-H3"},
                {"id": "MiniMax-H3-Context-IR"},
                {"id": "minimax-m2.7"},
            ]
        }, "apimart")

        self.assertEqual(ids, ["MiniMax-H3", "MiniMax-H3-Context-IR", "minimax-m2.7"])
        self.assertEqual(grouped["chat"], ["minimax-m2.7"])
        self.assertEqual(grouped["video"], ["MiniMax-H3", "MiniMax-H3-Context-IR"])

    def test_apimart_expanded_category_precedes_name_fallback(self):
        grouped, _ids = main.parse_upstream_models({
            "data": [
                {"id": "opaque-future-visual-model", "category": "video"},
                {"id": "name-contains-video-but-is-image", "category": "image"},
                {"id": "opaque-audio-model", "category": "audio"},
            ]
        }, "apimart")

        self.assertEqual(grouped["image"], ["name-contains-video-but-is-image"])
        self.assertEqual(grouped["video"], ["opaque-future-visual-model"])
        self.assertIn("opaque-audio-model", grouped["chat"])
        self.assertEqual(main.upstream_models_params("apimart"), {"expand": "category"})
        self.assertIsNone(main.upstream_models_params("openai"))

    def test_saved_apimart_category_errors_are_migrated(self):
        provider = main.normalize_provider({
            "id": "apimart",
            "name": "APIMART",
            "base_url": "https://api.apimart.ai",
            "protocol": "apimart",
            "image_models": ["text-moderation-stable"],
            "chat_models": ["MiniMax-H3", "grok-imagine-1.5-apimart"],
            "video_models": ["wan2.7-image"],
        })

        self.assertEqual(provider["image_models"], ["grok-imagine-1.5-apimart", "wan2.7-image"])
        self.assertEqual(provider["chat_models"], ["text-moderation-stable"])
        self.assertEqual(provider["video_models"], ["MiniMax-H3"])

    def test_apimart_h3_uses_unified_video_endpoints(self):
        provider = {"id": "apimart", "protocol": "apimart", "base_url": "https://api.apimart.ai"}
        self.assertEqual(
            main.video_submit_url_candidates(provider, "https://api.apimart.ai"),
            ["https://api.apimart.ai/v1/videos/generations"],
        )
        self.assertEqual(
            main.video_task_url_candidates(provider, "https://api.apimart.ai", "task-123"),
            ["https://api.apimart.ai/v1/tasks/task-123?language=zh"],
        )
        self.assertEqual(
            main.extract_task_id({"code": 200, "data": [{"status": "submitted", "task_id": "task-123"}]}),
            "task-123",
        )
        self.assertEqual(
            main.video_output_urls({
                "code": 200,
                "data": {"status": "completed", "result": {"videos": [{"url": ["https://example.com/h3.mp4"]}]}},
            }),
            ["https://example.com/h3.mp4"],
        )

    def test_paid_video_task_id_is_persisted_for_canvas_recovery(self):
        local_task_id = "canvas_video_test"
        old_task = main.CANVAS_TASKS.get(local_task_id)
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            main, "CANVAS_VIDEO_TASKS_FILE", str(Path(temp_dir) / "video_tasks.json")
        ):
            main.CANVAS_TASKS[local_task_id] = {
                "id": local_task_id,
                "type": "online-video",
                "status": "running",
                "provider_id": "apimart",
                "result": None,
            }
            token = main.CURRENT_CANVAS_VIDEO_TASK_ID.set(local_task_id)
            try:
                main.remember_canvas_video_upstream_task("task-paid-123", "https://api.apimart.ai/v1/videos/generations")
            finally:
                main.CURRENT_CANVAS_VIDEO_TASK_ID.reset(token)

            task = main.CANVAS_TASKS[local_task_id]
            self.assertEqual(task["status"], "waiting")
            self.assertEqual(task["upstream_task_id"], "task-paid-123")
            self.assertTrue(Path(main.CANVAS_VIDEO_TASKS_FILE).exists())

        if old_task is None:
            main.CANVAS_TASKS.pop(local_task_id, None)
        else:
            main.CANVAS_TASKS[local_task_id] = old_task

    def test_apimart_h3_body_matches_supported_parameters(self):
        payload = main.CanvasVideoRequest(
            prompt="test",
            provider_id="apimart",
            model="MiniMax-H3",
            duration=20,
            aspect_ratio="16:9",
            resolution="720p",
            watermark=True,
        )
        self.assertEqual(main.apimart_minimax_h3_video_body(payload, payload.model), {
            "model": "MiniMax-H3",
            "prompt": "test",
            "duration": 15,
            "resolution": "768P",
            "aspect_ratio": "16:9",
            "watermark": True,
        })

    def test_apimart_h3_rejects_incompatible_media_modes(self):
        with self.assertRaises(main.HTTPException) as mixed:
            main.validate_apimart_minimax_h3_media(
                [{"url": "https://example.com/start.png", "role": "first_frame"}],
                [],
                ["https://example.com/reference.mp4"],
                [],
            )
        self.assertEqual(mixed.exception.status_code, 400)

        with self.assertRaises(main.HTTPException) as audio_only:
            main.validate_apimart_minimax_h3_media(
                [], [], [], ["https://example.com/reference.mp3"]
            )
        self.assertEqual(audio_only.exception.status_code, 400)


class ApimartVideoPollingTests(unittest.IsolatedAsyncioTestCase):
    async def test_completed_status_waits_until_result_url_is_published(self):
        payloads = [
            {"code": 200, "data": {"id": "task-123", "status": "completed", "result": {}}},
            {
                "code": 200,
                "data": {
                    "id": "task-123",
                    "status": "completed",
                    "result": {"videos": [{"url": ["https://example.com/h3.mp4"]}]},
                },
            },
        ]

        class FakeResponse:
            def __init__(self, body):
                self._body = body

            def raise_for_status(self):
                return None

            def json(self):
                return self._body

        class FakeClient:
            async def get(self, _url, **_kwargs):
                return FakeResponse(payloads.pop(0))

        provider = {"id": "apimart", "protocol": "apimart", "base_url": "https://api.apimart.ai"}
        with patch.object(main.asyncio, "sleep", new=AsyncMock()):
            result = await main.wait_for_video_task(FakeClient(), provider, "task-123")

        self.assertEqual(main.video_output_urls(result), ["https://example.com/h3.mp4"])

    async def test_canvas_video_background_task_keeps_result_for_frontend_polling(self):
        local_task_id = "canvas_video_background_test"
        payload = main.CanvasVideoRequest(prompt="test", provider_id="apimart", model="MiniMax-H3")
        old_task = main.CANVAS_TASKS.get(local_task_id)
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.object(main, "CANVAS_VIDEO_TASKS_FILE", str(Path(temp_dir) / "video_tasks.json")),
                patch.object(
                    main,
                    "canvas_video",
                    new=AsyncMock(return_value={"videos": ["/assets/output/h3.mp4"], "task_id": "task-123"}),
                ),
            ):
                main.CANVAS_TASKS[local_task_id] = {
                    "id": local_task_id,
                    "type": "online-video",
                    "status": "queued",
                    "provider_id": "apimart",
                    "model": "MiniMax-H3",
                    "result": None,
                }
                await main.run_canvas_video_task(local_task_id, payload)
                task = main.CANVAS_TASKS[local_task_id]
                self.assertEqual(task["status"], "succeeded")
                self.assertEqual(task["result"]["videos"], ["/assets/output/h3.mp4"])

        if old_task is None:
            main.CANVAS_TASKS.pop(local_task_id, None)
        else:
            main.CANVAS_TASKS[local_task_id] = old_task


class ApimartMidjourneyRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_channel_failure_retries_until_task_is_accepted(self):
        responses = [
            {
                "status": 400,
                "body": {
                    "error": {
                        "message": "Please wait and try again later. Thank you for your patience!",
                        "type": "apimart_error",
                        "code": "get_channel_failed",
                    }
                },
            },
            {
                "status": 400,
                "body": {
                    "error": {
                        "message": "Please wait and try again later. Thank you for your patience!",
                        "type": "apimart_error",
                        "code": "get_channel_failed",
                    }
                },
            },
            {
                "status": 503,
                "body": {"error": {"message": "No available upstream", "code": "9"}},
            },
            {"status": 200, "body": {"data": {"task_id": "mj-task-123"}}},
        ]
        calls = []
        sleeps = []

        class FakeResponse:
            def __init__(self, item):
                self.status_code = item["status"]
                self._body = item["body"]
                self.text = ""

            def json(self):
                return self._body

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return False

            async def post(self, url, **kwargs):
                calls.append((url, kwargs))
                return FakeResponse(responses[len(calls) - 1])

        async def fake_sleep(delay):
            sleeps.append(delay)

        with (
            patch.object(main.httpx, "AsyncClient", side_effect=lambda **_kwargs: FakeClient()),
            patch.object(main, "api_headers", return_value={"Authorization": "Bearer test"}),
            patch.object(main.asyncio, "sleep", side_effect=fake_sleep),
        ):
            raw, task_id = await main.apimart_midjourney_request(
                {"id": "apimart"},
                "/v1/midjourney/generations",
                {"prompt": "test"},
            )

        self.assertEqual(task_id, "mj-task-123")
        self.assertEqual(raw["data"]["task_id"], "mj-task-123")
        self.assertEqual(len(calls), 4)
        self.assertEqual(sleeps, [1.0, 4.0, 16.0])

    async def test_normal_image_route_bridges_midjourney_to_task_api(self):
        provider = {
            "id": "apimart",
            "name": "APIMART",
            "base_url": "https://api.apimart.ai",
            "protocol": "apimart",
        }
        expected = ({"type": "url", "value": "https://example.com/mj.png"}, {"task_id": "mj-1"})
        bridge = AsyncMock(return_value=expected)
        with (
            patch.object(main, "get_api_provider", return_value=provider),
            patch.object(main, "generate_apimart_midjourney_image", bridge),
        ):
            result = await main.generate_ai_image(
                "test", "1024x1024", "high", "midjourney", [], "apimart", "16:9"
            )

        self.assertEqual(result, expected)
        bridge.assert_awaited_once_with("test", "1024x1024", "midjourney", [], provider, "16:9")

    async def test_midjourney_bridge_returns_completed_remote_image(self):
        provider = {"id": "apimart", "name": "APIMART", "protocol": "apimart"}
        submitted = AsyncMock(return_value=({"data": {"status": "queued"}}, "mj-task-456"))
        completed = AsyncMock(return_value=(
            "mj-task-456",
            {"data": {"status": "SUCCESS", "image_urls": ["https://example.com/result.png"]}},
        ))
        with (
            patch.object(main, "apimart_midjourney_request", submitted),
            patch.object(main, "apimart_midjourney_task_payload", completed),
            patch.object(main, "midjourney_reference_urls", AsyncMock(return_value=[])),
        ):
            image, raw = await main.generate_apimart_midjourney_image(
                "draw a lighthouse",
                "1920x1080",
                "midjourney",
                [],
                provider,
                "16:9",
            )

        self.assertEqual(image, {"type": "url", "value": "https://example.com/result.png"})
        self.assertEqual(raw["task_id"], "mj-task-456")
        submitted.assert_awaited_once()
        request_body = submitted.await_args.args[2]
        self.assertEqual(request_body["size"], "16:9")
        self.assertEqual(request_body["version"], "6.1")
        self.assertEqual(request_body["speed"], "relax")


if __name__ == "__main__":
    unittest.main()
