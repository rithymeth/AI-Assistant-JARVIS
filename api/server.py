import ipaddress
import json
import os
import sqlite3
import tempfile

import numpy as np
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config.settings import BASE_DIR, MODEL_NAME
from core.auth.face_sessions import create_session, verify_session
from core.auth.users import LOOPBACK_USER, User, generate_code, hash_new_code
from core.brain.agent import handle_message, list_pending_actions, resume_after_approval
from core.brain.llm import is_available
from core.memory.store import (
    add_face_embedding,
    create_user,
    find_user_by_code,
    get_face_embeddings,
    get_history,
    has_face_embeddings,
    init_db,
    list_due_undelivered_reminders,
    list_users,
)

app = FastAPI(title="Javi")

init_db()

# Requests from the machine itself never need the access code — only
# non-loopback (LAN) requests are gated, and only for endpoints that
# actually DO something (/chat drives the agent, which can call tools;
# /tools/approve executes an approval-gated action) or REVEAL something
# (/history shows past conversation content). /health and the static UI
# shell stay open so the page loads and can show its own code-entry prompt.
#
# /voice/* (transcribe, speak) and /vision/analyze are deliberately left
# ungated: they're audio/image I/O utilities that don't take actions or
# expose anything sensitive on their own. This matters in practice, not
# just in theory — standby listening calls /voice/transcribe on every
# detected sound, gated or not, so leaving it gated meant a stream of 401s
# from ambient noise alone, each one re-triggering the code prompt and
# fighting the user's own typing (a real, reported bug — see
# promptForAccessCode() in app.js for the actual race that caused it).
#
# RE-ENABLED: multi-user auth (per-user codes + roles, see core/auth/users.py
# and core/memory/store.py's `users` table) gives the gate something real to
# attach to — a LAN request now resolves to a specific user (not just a
# pass/fail against one shared secret), and /auth/* needs that resolution to
# answer "who am I" / manage accounts, so it's gated too. Loopback is and
# remains fully trusted regardless of this tuple (see _is_loopback_host below).
GATED_PREFIXES = ("/chat", "/tools/", "/history/", "/auth/", "/reminders/")

# Exempt from the face-session check below (but NOT from the code check
# above it) — this is the endpoint a LAN client calls to actually obtain a
# face-session token, so requiring one already would be a deadlock.
FACE_VERIFY_PATH = "/auth/face/verify"


def _is_loopback_host(host: str | None) -> bool:
    """Whether `host` (request.client.host) is the machine talking to
    itself. Deliberately does NOT trust the Host header (what the browser
    typed) — only the actual TCP peer address, since Host is trivially
    spoofable by anyone on the LAN and would defeat the whole gate.
    Uses ipaddress parsing rather than an exact-string set: a real desktop
    browser hitting literal "localhost" still showed the gate under the
    old set-based check, because "localhost" can resolve to a loopback
    address in more than one valid string form (compressed "::1",
    uncompressed "0:0:0:0:0:0:0:1", IPv4-mapped "::ffff:127.0.0.1") and a
    fixed set of literals can't anticipate all of them — parsing the
    address and asking whether it's actually loopback handles every form
    by construction instead of by enumeration."""
    if not host:
        return False
    if host == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_loopback


@app.middleware("http")
async def access_code_gate(request: Request, call_next):
    client_host = request.client.host if request.client else None
    if _is_loopback_host(client_host):
        # The person at the keyboard already had full control before any of
        # this existed — represented explicitly now as the synthetic admin
        # user rather than an implicit bypass.
        request.state.user = LOOPBACK_USER
        return await call_next(request)
    if not request.url.path.startswith(GATED_PREFIXES):
        return await call_next(request)
    supplied = (request.headers.get("X-Javi-Access-Code") or "").strip()
    resolved = find_user_by_code(supplied) if supplied else None
    if resolved is None:
        return JSONResponse(
            {"detail": "Missing or invalid access code", "seen_client_host": client_host},
            status_code=401,
        )
    request.state.user = User(id=resolved["id"], username=resolved["username"], role=resolved["role"])

    # Face 2FA is additive, not a replacement — only enforced for a user who
    # has actually enrolled a face (has_face_embeddings). A user who never
    # enrolled isn't affected at all, so this can't lock anyone out by
    # default; it only tightens things for whoever opted in.
    if request.url.path != FACE_VERIFY_PATH and has_face_embeddings(resolved["id"]):
        face_token = request.headers.get("X-Javi-Face-Session") or ""
        if not verify_session(face_token, resolved["id"]):
            return JSONResponse(
                {"detail": "Face verification required", "reason": "face_verification_required"},
                status_code=401,
            )

    return await call_next(request)


def _current_user(request: Request) -> User:
    return getattr(request.state, "user", LOOPBACK_USER)


def _require_admin(request: Request) -> User:
    user = _current_user(request)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin required")
    return user


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ApproveRequest(BaseModel):
    action_id: str
    approve: bool


class SpeakRequest(BaseModel):
    text: str


class MonitorStartRequest(BaseModel):
    interval_s: float | None = None


class CreateUserRequest(BaseModel):
    username: str
    role: str  # "admin" | "standard"


@app.get("/health")
def health():
    return {"status": "ok", "ollama_connected": is_available(), "model": MODEL_NAME}


@app.get("/history/{session_id}")
def history(session_id: str):
    return {"messages": get_history(session_id)}


def _sse(event: dict) -> str:
    event_type = event["type"]
    if event_type == "token":
        return f"data: {json.dumps({'token': event['content']})}\n\n"
    return f"event: {event_type}\ndata: {json.dumps({k: v for k, v in event.items() if k != 'type'})}\n\n"


def _stream(events) -> StreamingResponse:
    def event_stream():
        for event in events:
            yield _sse(event)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/chat")
def chat(req: ChatRequest, request: Request):
    return _stream(handle_message(req.session_id, req.message, _current_user(request)))


@app.post("/tools/approve")
def approve(req: ApproveRequest, request: Request):
    return _stream(resume_after_approval(req.action_id, req.approve, _current_user(request)))


@app.get("/tools/pending")
def tools_pending(request: Request):
    _require_admin(request)
    return {"pending": list_pending_actions()}


@app.get("/reminders/due")
def reminders_due():
    # Marks-and-returns atomically (see list_due_undelivered_reminders) so
    # a reminder is delivered exactly once even with more than one client
    # polling — no requester identity needed, reminders are global per the
    # single-household design (see core/memory/store.py's reminders table).
    return {"due": list_due_undelivered_reminders()}


@app.get("/auth/me")
def auth_me(request: Request):
    user = _current_user(request)
    return {"id": user.id, "username": user.username, "role": user.role}


@app.get("/auth/users")
def auth_list_users(request: Request):
    _require_admin(request)
    return {"users": list_users()}


@app.post("/auth/users")
def auth_create_user(req: CreateUserRequest, request: Request):
    _require_admin(request)
    if req.role not in ("admin", "standard"):
        raise HTTPException(status_code=400, detail="role must be 'admin' or 'standard'")
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="username is required")
    code = generate_code()
    code_hash, code_salt = hash_new_code(code)
    try:
        user_id = create_user(username, code_hash, code_salt, req.role)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="username already exists")
    # The generated code is only ever returned here, at creation time — it's
    # stored as a salted hash from this point on, same as the bootstrap
    # admin's code, so there's no way to recover it later if it's lost.
    return {"id": user_id, "username": username, "role": req.role, "code": code}


def _embed_uploaded_photo(raw_bytes: bytes, filename: str | None) -> np.ndarray:
    from core.auth.face import NoFaceDetected, embed_face

    suffix = os.path.splitext(filename or "")[1] or ".jpg"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw_bytes)
        try:
            return embed_face(tmp_path)
        except NoFaceDetected as e:
            raise HTTPException(status_code=400, detail=str(e))
    finally:
        os.remove(tmp_path)


@app.post("/auth/face/enroll")
async def face_enroll(request: Request, user_id: int = Form(...), photo: UploadFile = File(...)):
    # Independent of the code gate above (which /auth/ already goes
    # through) — enrollment is rejected for any non-loopback caller
    # outright, even one holding a perfectly valid code, since this is the
    # step that decides whose face counts as a match going forward.
    if not _is_loopback_host(request.client.host if request.client else None):
        raise HTTPException(status_code=403, detail="Face enrollment is only allowed from this machine")
    embedding = _embed_uploaded_photo(await photo.read(), photo.filename)
    add_face_embedding(user_id, embedding.astype(np.float32).tobytes())
    return {"status": "enrolled", "user_id": user_id}


@app.post("/auth/face/verify")
async def face_verify(request: Request, photo: UploadFile = File(...)):
    from core.auth.face import is_match

    user = _current_user(request)
    embedding = _embed_uploaded_photo(await photo.read(), photo.filename)
    enrolled = [np.frombuffer(b, dtype=np.float32) for b in get_face_embeddings(user.id)]
    if not is_match(embedding, enrolled):
        raise HTTPException(status_code=401, detail="Face did not match")
    return {"status": "verified", "face_session": create_session(user.id)}


@app.post("/vision/analyze")
async def vision_analyze(image: UploadFile):
    from vision.describe import analyze_image

    suffix = os.path.splitext(image.filename or "")[1] or ".jpg"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(await image.read())
        return analyze_image(tmp_path)
    finally:
        os.remove(tmp_path)


@app.post("/vision/camera/monitor/start")
def camera_monitor_start(req: MonitorStartRequest):
    from vision.camera_monitor import start_monitor

    kwargs = {"interval_s": req.interval_s} if req.interval_s else {}
    return start_monitor(**kwargs)


@app.post("/vision/camera/monitor/stop")
def camera_monitor_stop():
    from vision.camera_monitor import stop_monitor

    return stop_monitor()


@app.get("/vision/camera/monitor/status")
def camera_monitor_status():
    from vision.camera_monitor import get_status

    return get_status()


@app.get("/vision/camera/stream")
def camera_stream():
    from vision.camera_stream import mjpeg_frames

    return StreamingResponse(
        mjpeg_frames(), media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/vision/camera/detections")
def camera_detections():
    from vision.camera_stream import get_latest_detections

    return {"detections": get_latest_detections()}


@app.post("/voice/transcribe")
async def voice_transcribe(audio: UploadFile):
    from voice.stt import transcribe

    suffix = os.path.splitext(audio.filename or "")[1] or ".webm"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(await audio.read())
        return {"text": transcribe(tmp_path)}
    finally:
        os.remove(tmp_path)


@app.post("/voice/speak")
def voice_speak(req: SpeakRequest, background_tasks: BackgroundTasks):
    from voice.tts import speak_to_file

    fd, tmp_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    speak_to_file(req.text, tmp_path)
    background_tasks.add_task(os.remove, tmp_path)
    return FileResponse(tmp_path, media_type="audio/wav", filename="javi.wav")


app.mount("/", StaticFiles(directory=str(BASE_DIR / "ui" / "web"), html=True), name="ui")
