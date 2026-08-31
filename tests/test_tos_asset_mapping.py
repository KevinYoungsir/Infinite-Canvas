import hashlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


class FakeTosClient:
    def __init__(self, objects=None):
        self.objects = dict(objects or {})
        self.uploads = []
        self.acl_updates = []

    def head_object(self, bucket, key):
        if key not in self.objects:
            error = RuntimeError("NoSuchKey")
            error.status_code = 404
            error.code = "NoSuchKey"
            raise error
        return self.objects[key]

    def put_object_from_file(self, bucket, key, file_path, **kwargs):
        with open(file_path, "rb") as stream:
            raw = stream.read()
        self.uploads.append((bucket, key, kwargs))
        self.objects[key] = SimpleNamespace(content_length=len(raw), etag=hashlib.md5(raw).hexdigest())
        return SimpleNamespace(etag=self.objects[key].etag)

    def put_object_acl(self, bucket, key, **kwargs):
        self.acl_updates.append((bucket, key, kwargs))


def tos_provider(**overrides):
    provider = {
        "id": "volcengine",
        "volcengine_region": "cn-beijing",
        "volcengine_tos_bucket": "apimart-reference-video",
        "volcengine_tos_region": "cn-beijing",
        "volcengine_tos_endpoint": "tos-cn-beijing.volces.com",
        "volcengine_tos_prefix": "infinite-canvas",
        "volcengine_tos_access_mode": "public-read",
        "volcengine_tos_signed_expires": 604800,
        "volcengine_tos_auto_match": True,
    }
    provider.update(overrides)
    return provider


@pytest.fixture
def no_public_probe(monkeypatch):
    async def noop(_url):
        return None

    monkeypatch.setattr(main, "verify_tos_media_url", noop)
    monkeypatch.setattr(main, "volcengine_access_key_value", lambda: "ak-test")
    monkeypatch.setattr(main, "volcengine_secret_key_value", lambda: "sk-test")


@pytest.mark.asyncio
async def test_tos_matches_existing_console_upload_by_original_name_size_and_etag(tmp_path, monkeypatch, no_public_probe):
    raw = b"existing-video-content"
    path = tmp_path / "lib_1190815af4ab_Reference A.mp4"
    path.write_bytes(raw)
    head = SimpleNamespace(content_length=len(raw), etag=hashlib.md5(raw).hexdigest())
    fake = FakeTosClient({"Reference A.mp4": head})
    import tos
    monkeypatch.setattr(tos, "TosClientV2", lambda *args, **kwargs: fake)
    monkeypatch.setattr(main, "output_file_from_url", lambda _url: str(path))
    item = {"id": "asset-a", "url": "/assets/library/lib_1190815af4ab_Reference%20A.mp4", "kind": "video"}

    url = await main.ensure_asset_item_tos_url(item, tos_provider())

    assert url == "https://apimart-reference-video.tos-cn-beijing.volces.com/Reference%20A.mp4"
    assert fake.uploads == []
    assert fake.acl_updates and fake.acl_updates[0][1] == "Reference A.mp4"
    assert item["remote_sources"]["tos"]["object_key"] == "Reference A.mp4"
    assert item["remote_sources"]["tos"]["matched_existing"] is True


@pytest.mark.asyncio
async def test_tos_does_not_reuse_same_name_with_different_content(tmp_path, monkeypatch, no_public_probe):
    raw = b"new-video-content"
    path = tmp_path / "lib_1190815af4ab_Reference A.mp4"
    path.write_bytes(raw)
    wrong = SimpleNamespace(content_length=len(raw), etag="0" * 32)
    fake = FakeTosClient({"Reference A.mp4": wrong})
    import tos
    monkeypatch.setattr(tos, "TosClientV2", lambda *args, **kwargs: fake)
    monkeypatch.setattr(main, "output_file_from_url", lambda _url: str(path))
    item = {"id": "asset-a", "url": "/assets/library/lib_1190815af4ab_Reference%20A.mp4", "kind": "video"}

    await main.ensure_asset_item_tos_url(item, tos_provider())

    expected = f"infinite-canvas/{hashlib.sha256(raw).hexdigest()[:12]}_Reference A.mp4"
    assert fake.uploads and fake.uploads[0][1] == expected
    assert item["remote_sources"]["tos"]["object_key"] == expected
    assert item["remote_sources"]["tos"]["matched_existing"] is False


def test_normalize_provider_retains_tos_configuration():
    provider = main.normalize_provider(tos_provider(
        name="火山引擎",
        base_url=main.VOLCENGINE_DEFAULT_BASE_URL,
        protocol="volcengine",
        volcengine_tos_public_base_url="https://media.example.com/",
        volcengine_tos_region="cn-guangzhou",
        volcengine_tos_access_mode="signed",
        volcengine_tos_auto_match=False,
    ))

    assert provider["volcengine_tos_bucket"] == "apimart-reference-video"
    assert provider["volcengine_tos_public_base_url"] == "https://media.example.com"
    assert provider["volcengine_region"] == "cn-beijing"
    assert provider["volcengine_tos_region"] == "cn-guangzhou"
    assert provider["volcengine_tos_access_mode"] == "signed"
    assert provider["volcengine_tos_auto_match"] is False


@pytest.mark.asyncio
async def test_local_asset_tos_lookup_persists_mapping(monkeypatch):
    item = {"id": "asset-a", "url": "/assets/library/Reference%20A.mp4", "kind": "video"}
    lib = {"libraries": [{"id": "default", "categories": [{"id": "video", "items": [item]}]}]}
    saved = []

    monkeypatch.setattr(main, "volcengine_tos_is_configured", lambda provider=None: True)
    monkeypatch.setattr(main, "load_asset_library", lambda: lib)
    monkeypatch.setattr(main, "save_asset_library", lambda value: saved.append(value))

    async def ensure(target, provider=None):
        target["remote_sources"] = {"tos": {"object_key": "Reference A.mp4"}}
        return "https://example.com/Reference%20A.mp4"

    monkeypatch.setattr(main, "ensure_asset_item_tos_url", ensure)
    url = await main.local_asset_tos_public_url("/assets/library/Reference%20A.mp4")

    assert url.startswith("https://")
    assert saved == [lib]
