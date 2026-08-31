import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


class ApimartLocalVideoUploadTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        main.PUBLIC_MEDIA_UPLOAD_CACHE.clear()

    async def test_local_video_is_automatically_uploaded_and_cached(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            tmp.write(b"fake-video")
            tmp.flush()
            uploader = AsyncMock(return_value={
                "url": "https://files.example/reference.mp4",
                "service": "test",
                "expires": "72h",
            })
            with (
                patch.object(main, "local_asset_public_url", return_value=""),
                patch.object(main, "output_file_from_url", return_value=tmp.name),
                patch.object(main, "content_type_for_path", return_value="video/mp4"),
                patch.object(main, "upload_local_video_to_cloud", uploader),
                patch.dict(os.environ, {"APIMART_AUTO_PUBLICIZE_LOCAL_VIDEO": "1"}, clear=False),
            ):
                first = await main.upload_video_for_apimart(object(), {}, "/assets/library/reference.mp4")
                second = await main.upload_video_for_apimart(object(), {}, "/assets/library/reference.mp4")

        self.assertEqual(first, "https://files.example/reference.mp4")
        self.assertEqual(second, first)
        uploader.assert_awaited_once()

    async def test_configured_public_media_url_still_takes_priority(self):
        uploader = AsyncMock()
        with (
            patch.object(main, "local_asset_public_url", return_value="https://media.example/assets/reference.mp4"),
            patch.object(main, "upload_local_video_to_cloud", uploader),
        ):
            result = await main.upload_video_for_apimart(object(), {}, "/assets/library/reference.mp4")

        self.assertEqual(result, "https://media.example/assets/reference.mp4")
        uploader.assert_not_awaited()

    async def test_registered_asset_uri_is_resolved_to_tos_https_for_video_urls(self):
        item = {
            "id": "asset-1",
            "url": "/assets/library/reference.mp4",
            "registrations": {
                "apimart": {"asset_uri": "asset://asset-123", "status": "Active"},
            },
            "remote_sources": {
                "tos": {
                    "url": "https://bucket.tos-cn-guangzhou.volces.com/reference.mp4",
                    "access_mode": "public-read",
                },
            },
        }
        library = {
            "libraries": [{"id": "default", "categories": [{"id": "video", "items": [item]}]}],
        }
        with patch.object(main, "load_asset_library", return_value=library):
            result = await main.registered_asset_tos_http_url("asset://asset-123")

        self.assertEqual(result, "https://bucket.tos-cn-guangzhou.volces.com/reference.mp4")

    async def test_upload_video_never_passes_asset_uri_into_video_urls(self):
        resolver = AsyncMock(return_value="https://bucket.tos-cn-guangzhou.volces.com/reference.mp4")
        with patch.object(main, "registered_asset_tos_http_url", resolver):
            result = await main.upload_video_for_apimart(object(), {}, "asset://asset-123")

        self.assertTrue(main.valid_apimart_video_url(result))
        self.assertFalse(result.startswith("asset://"))
        resolver.assert_awaited_once_with("asset://asset-123")

    async def test_cloud_upload_failure_returns_actionable_error(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            tmp.write(b"fake-video")
            tmp.flush()
            with (
                patch.object(main, "local_asset_public_url", return_value=""),
                patch.object(main, "output_file_from_url", return_value=tmp.name),
                patch.object(main, "content_type_for_path", return_value="video/mp4"),
                patch.object(
                    main,
                    "upload_local_video_to_cloud",
                    AsyncMock(side_effect=main.HTTPException(status_code=502, detail="测试上传服务不可用")),
                ),
                patch.dict(
                    os.environ,
                    {
                        "APIMART_AUTO_PUBLICIZE_LOCAL_VIDEO": "1",
                        "APIMART_TRY_VIDEO_UPLOAD": "0",
                    },
                    clear=False,
                ),
            ):
                result = await main.upload_video_for_apimart(object(), {}, "/assets/library/reference.mp4")

        self.assertTrue(result.startswith("ERR:本地视频自动上传公网临时存储失败"))
        self.assertIn("测试上传服务不可用", result)

    async def test_volcengine_registration_also_publicizes_local_video(self):
        item = {
            "id": "asset-1",
            "name": "Reference A",
            "kind": "video",
            "url": "/assets/library/reference.mp4",
            "registrations": {},
        }
        provider = {
            "id": "volcengine",
            "protocol": "volcengine",
            "volcengine_project_name": "default",
        }
        publicizer = AsyncMock(return_value={"url": "https://files.example/reference.mp4"})
        submitter = AsyncMock(return_value="task-1")
        with (
            patch.object(main, "load_asset_library", return_value={}),
            patch.object(main, "find_asset_item_in_library", return_value=item),
            patch.object(main, "get_api_provider", return_value=provider),
            patch.object(main, "avatar_platform_for_provider", return_value="volcengine"),
            patch.object(main, "volcengine_public_asset_url", return_value="ERR:需要公网地址"),
            patch.object(main, "output_file_from_url", return_value="D:/tmp/reference.mp4"),
            patch.object(main, "cached_public_media_upload", publicizer),
            patch.object(main, "submit_volcengine_avatar_asset", submitter),
            patch.object(main, "save_asset_library"),
        ):
            result = await main.register_asset_library_avatar(
                "asset-1",
                main.AssetAvatarRegisterRequest(provider_id="volcengine"),
            )

        publicizer.assert_awaited_once()
        submitter.assert_awaited_once()
        self.assertEqual(result["item"]["registrations"]["volcengine"]["status"], "Processing")


if __name__ == "__main__":
    unittest.main()
