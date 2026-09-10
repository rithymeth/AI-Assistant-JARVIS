import asyncio
import os
import sys
import tempfile
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

TEST_DIR = tempfile.TemporaryDirectory()
os.environ.setdefault("DB_PATH", os.path.join(TEST_DIR.name, "test.db"))

if "fastapi" not in sys.modules:
    fastapi = types.ModuleType("fastapi")
    responses = types.ModuleType("fastapi.responses")
    staticfiles = types.ModuleType("fastapi.staticfiles")
    pydantic = types.ModuleType("pydantic")

    class DummyFastAPI:
        def __init__(self, *args, **kwargs):
            pass

        def middleware(self, *_args, **_kwargs):
            return lambda fn: fn

        def get(self, *_args, **_kwargs):
            return lambda fn: fn

        def post(self, *_args, **_kwargs):
            return lambda fn: fn

        def mount(self, *_args, **_kwargs):
            return None

    class DummyHTTPException(Exception):
        def __init__(self, status_code, detail):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class DummyJSONResponse:
        def __init__(self, content, status_code=200):
            self.content = content
            self.status_code = status_code
            self.body = str(content).encode()

    class DummyStreamingResponse:
        def __init__(self, body, media_type=None):
            self.body = body
            self.media_type = media_type

    class DummyFileResponse:
        def __init__(self, path, media_type=None, filename=None):
            self.path = path
            self.media_type = media_type
            self.filename = filename

    class DummyStaticFiles:
        def __init__(self, *args, **kwargs):
            pass

    class DummyBaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    fastapi.BackgroundTasks = object
    fastapi.FastAPI = DummyFastAPI
    fastapi.File = lambda *args, **kwargs: None
    fastapi.Form = lambda *args, **kwargs: None
    fastapi.HTTPException = DummyHTTPException
    fastapi.Request = object
    fastapi.UploadFile = object
    responses.FileResponse = DummyFileResponse
    responses.JSONResponse = DummyJSONResponse
    responses.StreamingResponse = DummyStreamingResponse
    staticfiles.StaticFiles = DummyStaticFiles
    pydantic.BaseModel = DummyBaseModel

    sys.modules["fastapi"] = fastapi
    sys.modules["fastapi.responses"] = responses
    sys.modules["fastapi.staticfiles"] = staticfiles
    sys.modules["pydantic"] = pydantic

from core.auth.users import LOOPBACK_USER
from core.memory import store
from api import server

store.init_db()


class DummyRequest:
    def __init__(self, host, path, headers=None):
        self.client = SimpleNamespace(host=host)
        self.url = SimpleNamespace(path=path)
        self.headers = headers or {}
        self.state = SimpleNamespace()


class ServerTests(unittest.TestCase):
    def test_is_loopback_host_recognizes_common_variants(self):
        self.assertTrue(server._is_loopback_host("localhost"))
        self.assertTrue(server._is_loopback_host("127.0.0.1"))
        self.assertTrue(server._is_loopback_host("::1"))
        self.assertTrue(server._is_loopback_host("::ffff:127.0.0.1"))
        self.assertFalse(server._is_loopback_host("192.168.1.20"))

    def test_sse_formats_token_and_named_events(self):
        token_evt = server._sse({"type": "token", "content": "Hi"})
        named_evt = server._sse({"type": "tool_call", "tool": "web_search"})

        self.assertEqual(token_evt, 'data: {"token": "Hi"}\n\n')
        self.assertEqual(named_evt, 'event: tool_call\ndata: {"tool": "web_search"}\n\n')

    def test_access_code_gate_allows_loopback_without_code(self):
        request = DummyRequest("127.0.0.1", "/chat")

        async def call_next(req):
            return {"ok": True, "user": req.state.user}

        result = asyncio.run(server.access_code_gate(request, call_next))

        self.assertEqual(result["user"], LOOPBACK_USER)

    def test_access_code_gate_requires_face_verification_when_enrolled(self):
        request = DummyRequest("192.168.1.20", "/chat", {"X-Javi-Access-Code": "ABCD1234"})
        resolved = {"id": 2, "username": "pat", "role": "standard"}

        async def call_next(_req):
            return {"ok": True}

        with (
            patch.object(server, "find_user_by_code", return_value=resolved),
            patch.object(server, "has_face_embeddings", return_value=True),
            patch.object(server, "verify_session", return_value=False),
        ):
            response = asyncio.run(server.access_code_gate(request, call_next))

        self.assertEqual(response.status_code, 401)
        self.assertIn("face_verification_required", response.body.decode())


if __name__ == "__main__":
    unittest.main()
