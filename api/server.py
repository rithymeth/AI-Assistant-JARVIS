import ipaddress
import json
import os
import sqlite3
import tempfile
from typing import Any

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
# /voice/* (transcribe, speak) stays ungated: standby listening calls
# /voice/transcribe on every detected sound, gated or not, so leaving it
# gated meant a stream of 401s from ambient noise alone, each one
# re-triggering the code prompt (see promptForAccessCode() in app.js).
# /vision/* IS gated — camera stream/monitor/analyze expose the webcam
# and must not be open on the LAN.
#
# RE-ENABLED: multi-user auth (per-user codes + roles, see core/auth/users.py
# and core/memory/store.py's `users` table) gives the gate something real to
# attach to — a LAN request now resolves to a specific user (not just a
# pass/fail against one shared secret), and /auth/* needs that resolution to
# answer "who am I" / manage accounts, so it's gated too. Loopback is and
# remains fully trusted regardless of this tuple (see _is_loopback_host below).
GATED_PREFIXES = ("/chat", "/tools/", "/history/", "/auth/", "/reminders/", "/vision/")

# Exempt from the face-session check below (but NOT from the code check
# above it) — this is the endpoint a LAN client calls to actually obtain a
# face-session token, so requiring one already would be a deadlock.
FACE_VERIFY_PATH = "/auth/face/verify"
