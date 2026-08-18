const statusDot = document.getElementById("status-dot");
const cameraMonitorDot = document.getElementById("camera-monitor-dot");
const cameraMonitorToggle = document.getElementById("camera-monitor-toggle");
const cameraPanel = document.getElementById("camera-panel");
const cameraFeedImg = document.getElementById("camera-feed-img");
const cameraDetectionsList = document.getElementById("camera-detections-list");
const orbEl = document.getElementById("jarvis-orb");
const clockEl = document.getElementById("jarvis-clock");
const stateEl = document.getElementById("jarvis-state");
const captionEl = document.getElementById("jarvis-caption");
const approvalContainer = document.getElementById("approval-container");
const adminPendingContainer = document.getElementById("admin-pending-container");

const SESSION_KEY = "javi_session_id";
let sessionId = localStorage.getItem(SESSION_KEY);
if (!sessionId) {
  sessionId = crypto.randomUUID();
  localStorage.setItem(SESSION_KEY, sessionId);
}

/* ---------- access code (LAN access only — the server never asks for one
 * when reached via localhost, so this whole flow is a no-op on this
 * machine and only matters when a phone hits it over WiFi) ---------- */

const ACCESS_CODE_KEY = "javi_access_code";
const accessGateEl = document.getElementById("access-gate");
const accessCodeInput = document.getElementById("access-code-input");
const accessCodeSubmit = document.getElementById("access-code-submit");

function getStoredAccessCode() {
  return localStorage.getItem(ACCESS_CODE_KEY) || "";
}

// Singleton: apiFetch() gets called from several independent places (a
// user-triggered chat, standby listening retrying on every detected sound,
// TTS playback, etc.), and any of them can 401 around the same time. If
// each call opened its OWN promise here, every one would reset the input
// back to "" and re-attach its own listeners on the same shared DOM nodes —
// so a background retry landing mid-typing (or right as you hit Unlock)
// would silently wipe what you'd typed, and the click would read an empty
// field and no-op. This was a real, reported bug, not hypothetical. Fixed
// by making concurrent callers share the one pending prompt instead of
// each spawning a new one.
let pendingAccessCodePrompt = null;

function promptForAccessCode() {
  if (pendingAccessCodePrompt) return pendingAccessCodePrompt;

  pendingAccessCodePrompt = new Promise((resolve) => {
    accessGateEl.hidden = false;
    accessCodeInput.value = "";
    accessCodeInput.focus();

    const onSubmit = () => {
      const code = accessCodeInput.value.trim();
      if (!code) return;
      localStorage.setItem(ACCESS_CODE_KEY, code);
      accessGateEl.hidden = true;
      accessCodeSubmit.removeEventListener("click", onSubmit);
      accessCodeInput.removeEventListener("keydown", onKeydown);
      pendingAccessCodePrompt = null;
      resolve(code);
    };
    const onKeydown = (e) => {
      if (e.key === "Enter") onSubmit();
    };

    accessCodeSubmit.addEventListener("click", onSubmit);
    accessCodeInput.addEventListener("keydown", onKeydown);
  });

  return pendingAccessCodePrompt;
}

/* ---------- face verification (session-scoped second factor — only
 * triggers for a user who has actually enrolled a face via enroll.html;
 * everyone else never sees this) ---------- */

const FACE_SESSION_KEY = "javi_face_session";

function getStoredFaceSession() {
  return localStorage.getItem(FACE_SESSION_KEY) || "";
}

// Grabs one still frame from the camera via a short-lived getUserMedia
// stream (distinct from the standby mic stream, and from vision/camera.py's
// server-side webcam capture — this is deliberately the *requesting
// device's* camera, since it's proving who's holding THIS device, e.g. a
// phone on the LAN).
async function captureFacePhoto() {
  const stream = await navigator.mediaDevices.getUserMedia({ video: true });
  try {
    const video = document.createElement("video");
    video.srcObject = stream;
    video.muted = true;
    await video.play();
    await sleep(400); // let exposure/focus settle before snapping
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    return await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.9));
  } finally {
    stream.getTracks().forEach((t) => t.stop());
  }
}

// Singleton for the same reason as promptForAccessCode() above: several
// independent apiFetch() callers can hit the face-required 401 around the
// same time, and each shouldn't open its own camera stream.
let pendingFaceVerificationPrompt = null;

function promptForFaceVerification() {
  if (pendingFaceVerificationPrompt) return pendingFaceVerificationPrompt;

  pendingFaceVerificationPrompt = (async () => {
    setCaption("Face verification needed — look at the camera...");
    try {
      const photo = await captureFacePhoto();
      const form = new FormData();
      form.append("photo", photo, "face.jpg");
      const code = getStoredAccessCode();
      const res = await fetch("/auth/face/verify", {
        method: "POST",
        headers: code ? { "X-Javi-Access-Code": code } : {},
        body: form,
      });
      if (!res.ok) {
        setCaption("Face verification failed — try again.");
        return false;
      }
      const data = await res.json();
      localStorage.setItem(FACE_SESSION_KEY, data.face_session);
      setCaption("Face verified.");
      return true;
    } catch {
      setCaption("Couldn't access the camera for face verification.");
      return false;
    }
  })();

  const clear = () => {
    pendingFaceVerificationPrompt = null;
  };
  pendingFaceVerificationPrompt.then(clear, clear);
  return pendingFaceVerificationPrompt;
}

// Drop-in replacement for fetch() on gated endpoints: attaches the stored
// access code and face-session token (both harmless no-ops if the server
// doesn't require them, i.e. every request from this machine itself). On a
// 401, distinguishes WHICH prompt to show by the response's `reason` field:
// `face_verification_required` means the code was fine but a second-factor
// face check is needed (see api/server.py's access_code_gate); anything
// else means the code itself was missing/wrong. Either way, retries once
// after the relevant prompt resolves. Never touches options.headers'
// Content-Type, so FormData uploads (their own auto-set multipart
// boundary) still work.
async function apiFetch(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  const code = getStoredAccessCode();
  if (code) headers["X-Javi-Access-Code"] = code;
  const faceSession = getStoredFaceSession();
  if (faceSession) headers["X-Javi-Face-Session"] = faceSession;

  let res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    let reason = null;
    try {
      reason = (await res.clone().json()).reason;
    } catch {
      // non-JSON error body — fall through to the generic code prompt
    }
    if (reason === "face_verification_required") {
      await promptForFaceVerification();
      res = await fetch(url, { ...options, headers: { ...headers, "X-Javi-Face-Session": getStoredFaceSession() } });
    } else {
      await promptForAccessCode();
      res = await fetch(url, { ...options, headers: { ...headers, "X-Javi-Access-Code": getStoredAccessCode() } });
    }
  }
  return res;
}

/* ---------- orb / clock / caption ---------- */

const ORB_STATE_LABELS = {
  idle: "STANDBY",
  thinking: "PROCESSING",
  speaking: "SPEAKING",
  listening: "LISTENING",
  offline: "OFFLINE",
  muted: "MUTED",
};

function setOrbState(state) {
  orbEl.className = `jarvis-orb ${state === "idle" ? "" : state}`.trim();
  stateEl.textContent = ORB_STATE_LABELS[state] || state.toUpperCase();
}

function tickClock() {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  const ss = String(now.getSeconds()).padStart(2, "0");
  clockEl.textContent = `${hh}:${mm}:${ss}`;
}
setInterval(tickClock, 1000);
tickClock();

let captionTimer = null;
function setCaption(text) {
  captionEl.textContent = text;
  captionEl.classList.add("visible");
  if (captionTimer) clearTimeout(captionTimer);
  captionTimer = setTimeout(() => captionEl.classList.remove("visible"), 8000);
}

/* ---------- voice out ---------- */

function speakText(text) {
  return new Promise((resolve) => {
    if (!text || !text.trim()) {
      resolve();
      return;
    }
    setCaption(text);
    setOrbState("speaking");
    (async () => {
      try {
        const res = await apiFetch("/voice/speak", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });
        if (!res.ok) {
          setOrbState("idle");
          resolve();
          return;
        }
        const blob = await res.blob();
        const audio = new Audio(URL.createObjectURL(blob));
        audio.addEventListener("ended", () => {
          setOrbState("idle");
          resolve();
        });
        audio.addEventListener("error", () => {
          setOrbState("idle");
          resolve();
        });
        audio.play();
      } catch {
        setOrbState("idle");
        resolve();
      }
    })();
  });
}

/* ---------- voice in: always-on standby listening (voice-activity detection) ---------- */

// No click needed to activate — the mic stays open and Javi automatically
// starts capturing whenever it hears speech, using an adaptive threshold
// (see "adaptive noise floor" below) instead of one fixed constant.
const SILENCE_MS = 1200;
const MIN_SPEECH_MS = 300;
const MAX_RECORD_MS = 20000;

// Wake-word gating: this is transcribe-then-filter, not real-time keyword
// spotting (there's no dedicated always-running wake-word model here —
// that's a separate, bigger build). Every speech segment the VAD captures
// gets transcribed via the existing Whisper pipeline, THEN checked for a
// wake word before anything is sent to the agent. Costs the same STT call
// either way, but means Javi only acts when addressed by name instead of
// reacting to all ambient conversation.
const WAKE_WORDS = ["hey javi", "hey jarvis", "javi", "jarvis"];

// Returns the command text after the wake word (possibly empty, if the user
// just said "Javi" alone), or null if no wake word was heard at all.
function stripWakeWord(text) {
  const lower = text.toLowerCase();
  const byLength = [...WAKE_WORDS].sort((a, b) => b.length - a.length);
  for (const word of byLength) {
    const idx = lower.indexOf(word);
    if (idx !== -1) {
      return text
        .slice(idx + word.length)
        .replace(/^[\s,.:;!?-]+/, "")
        .trim();
    }
  }
  return null;
}

let micStream = null;
let audioCtx = null;
let analyser = null;
let muted = false;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getVolume() {
  if (!analyser) return 0;
  const data = new Uint8Array(analyser.frequencyBinCount);
  analyser.getByteTimeDomainData(data);
  let sumSquares = 0;
  for (let i = 0; i < data.length; i++) {
    const v = (data[i] - 128) / 128;
    sumSquares += v * v;
  }
  return Math.sqrt(sumSquares / data.length);
}

/* ---------- adaptive noise floor ----------
 * VOICE_THRESHOLD used to be a fixed constant that needed hand-tuning per
 * mic/room. Instead, track a running estimate of the ambient noise floor —
 * an EMA over volume samples taken while presumed silent — and trigger on
 * floor + a fixed margin. This adapts on its own as room noise changes
 * (AC cycling, a TV elsewhere) instead of requiring a manual re-tune. */
const NOISE_FLOOR_MARGIN = 0.015; // how far above the floor counts as speech
const MIN_THRESHOLD = 0.01; // never below mic self-noise
const MAX_THRESHOLD = 0.2; // never so high a loud transient locks out real speech
const NOISE_FLOOR_EMA_ALPHA = 0.05; // slow ongoing adaptation while idle
const CALIBRATION_MS = 800; // initial burst on mic start, faster than the EMA alone

let noiseFloor = 0.005;
let voiceThreshold = MIN_THRESHOLD;

function updateVoiceThreshold() {
  voiceThreshold = Math.min(MAX_THRESHOLD, Math.max(MIN_THRESHOLD, noiseFloor + NOISE_FLOOR_MARGIN));
}

// Folds one volume sample taken while presumed silent into the running
// noise floor. Called continuously during standby, not just once at boot,
// so the threshold keeps tracking the room instead of going stale.
function observeSilenceSample(vol) {
  noiseFloor += NOISE_FLOOR_EMA_ALPHA * (vol - noiseFloor);
  updateVoiceThreshold();
}

// Samples ambient volume for a short burst right after the mic opens so the
// floor starts near-correct instead of drifting up from the low seed value
// over many slow EMA steps.
async function calibrateNoiseFloor(durationMs = CALIBRATION_MS) {
  const samples = [];
  const start = Date.now();
  while (Date.now() - start < durationMs) {
    samples.push(getVolume());
    await sleep(50);
  }
  if (samples.length) {
    samples.sort((a, b) => a - b);
    noiseFloor = samples[Math.floor(samples.length / 2)]; // median: robust to one loud blip
    updateVoiceThreshold();
  }
}

async function initStandbyMic() {
  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    setCaption("Couldn't access the microphone — standby listening is unavailable.");
    return false;
  }
  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const source = audioCtx.createMediaStreamSource(micStream);
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 512;
  source.connect(analyser);
  await calibrateNoiseFloor();
  return true;
}

async function transcribeBlob(blob) {
  const form = new FormData();
  form.append("audio", blob, "recording.webm");
  try {
    const res = await apiFetch("/voice/transcribe", { method: "POST", body: form });
    const data = await res.json();
    return data.text || "";
  } catch {
    return "";
  }
}

// Records from the shared standby stream until ~1.2s of silence follows
// speech (or maxMs is hit), then transcribes. Used both by passive standby
// listening and by the voice-approval flow below.
async function listenForSpeech(maxMs = MAX_RECORD_MS) {
  if (!micStream) return "";
  const chunks = [];
  const recorder = new MediaRecorder(micStream);
  recorder.ondataavailable = (e) => {
    if (e.data.size > 0) chunks.push(e.data);
  };
  const stopped = new Promise((resolve) => {
    recorder.onstop = resolve;
  });
  recorder.start();
  setOrbState("listening");

  const start = Date.now();
  let lastLoud = Date.now();
  while (true) {
    await sleep(100);
    if (getVolume() > voiceThreshold) lastLoud = Date.now();
    if (Date.now() - lastLoud > SILENCE_MS || Date.now() - start > maxMs) break;
  }
  recorder.stop();
  await stopped;

  if (Date.now() - start < MIN_SPEECH_MS) {
    setOrbState(muted ? "muted" : "idle");
    return "";
  }
  setOrbState("thinking");
  return transcribeBlob(new Blob(chunks, { type: "audio/webm" }));
}

function isBusy() {
  return (
    orbEl.className.includes("thinking") ||
    orbEl.className.includes("speaking") ||
    orbEl.className.includes("listening")
  );
}

async function standbyLoop() {
  let lastDisplayed = null;
  while (true) {
    if (!micStream) {
      await sleep(1000);
      continue;
    }
    if (muted) {
      if (lastDisplayed !== "muted") {
        setOrbState("muted");
        lastDisplayed = "muted";
      }
      await sleep(200);
      continue;
    }
    if (isBusy()) {
      lastDisplayed = null;
      await sleep(150);
      continue;
    }
    if (lastDisplayed !== "idle") {
      setOrbState("idle");
      lastDisplayed = "idle";
    }

    const vol = getVolume();
    if (vol > voiceThreshold) {
      lastDisplayed = null;
      const text = await listenForSpeech();
      if (!text || !text.trim()) {
        setOrbState(muted ? "muted" : "idle");
      } else {
        const command = stripWakeWord(text);
        if (command === null) {
          // Heard speech, but not addressed to Javi — ignore it.
          setOrbState(muted ? "muted" : "idle");
        } else if (command === "") {
          // Wake word alone ("Javi?") — acknowledge and listen for the
          // actual command as a direct follow-up, no wake word needed again.
          await speakText("Yes?");
          const followUp = await listenForSpeech(8000);
          if (followUp && followUp.trim()) {
            setCaption(`You: ${followUp}`);
            await sendToChat(followUp);
          } else {
            setOrbState(muted ? "muted" : "idle");
          }
        } else {
          setCaption(`You: ${command}`);
          await sendToChat(command);
        }
      }
    } else {
      observeSilenceSample(vol);
      await sleep(150);
    }
  }
}

// The orb no longer needs a click to activate — clicking it now toggles a
// manual mute, a deliberate pause on top of always-on standby (e.g. for a
// private conversation nearby, or before recording your own audio/video).
orbEl.addEventListener("click", () => {
  muted = !muted;
  setOrbState(muted ? "muted" : "idle");
  setCaption(muted ? "Standby paused — click the orb to resume listening." : "Standby listening resumed.");
});

/* ---------- approval (voice-first, visual fallback) ---------- */

const YES_WORDS = ["yes", "yeah", "yep", "sure", "go ahead", "approve", "confirm", "do it", "okay", "ok"];
const NO_WORDS = ["no", "nope", "don't", "do not", "stop", "cancel", "deny", "negative"];

function parseYesNo(text) {
  const t = text.toLowerCase();
  if (NO_WORDS.some((w) => t.includes(w))) return false;
  if (YES_WORDS.some((w) => t.includes(w))) return true;
  return false; // fail closed: unclear or silent answer never approves
}

// Polls this session's own history until a new message shows up (added once
// resume_after_approval finishes running — see core/brain/agent.py). Needed
// for the "waiting for admin" case: the admin resolves the request from
// their OWN /tools/approve call, on a different connection (possibly a
// different device entirely), so this browser has no live stream to read
// the outcome from — history is the one thing both sides agree on.
async function waitForApprovalResolution() {
  let baseline = null;
  while (true) {
    try {
      const res = await apiFetch(`/history/${sessionId}`);
      const data = await res.json();
      const messages = data.messages || [];
      if (baseline === null) {
        baseline = messages.length;
      } else if (messages.length > baseline) {
        const last = messages[messages.length - 1];
        if (last.role === "assistant" && last.content) {
          await speakText(last.content);
        } else {
          setOrbState(muted ? "muted" : "idle");
        }
        return;
      }
    } catch {
      // transient — keep polling
    }
    await sleep(2000);
  }
}

async function handlePendingAction(actionId, tool, args, description, requiresAdmin) {
  approvalContainer.innerHTML = "";
  const card = document.createElement("div");
  card.className = "approval-card";

  const label = document.createElement("div");
  label.className = "approval-label";
  label.textContent = `PENDING APPROVAL — ${tool}`;
  card.appendChild(label);

  const desc = document.createElement("div");
  desc.className = "approval-desc";
  desc.textContent = description;
  card.appendChild(desc);

  const isAdmin = !!(currentUser && currentUser.role === "admin");

  if (requiresAdmin && !isAdmin) {
    // Standard users can never self-approve an approval-gated tool call
    // (enforced server-side too, in resume_after_approval) — no buttons
    // here, just a wait state until an admin resolves it elsewhere.
    const waiting = document.createElement("div");
    waiting.className = "approval-waiting";
    waiting.textContent = "Waiting for an admin to approve this...";
    card.appendChild(waiting);
    approvalContainer.appendChild(card);

    setOrbState("thinking");
    await speakText(`I need an admin to approve this: ${description}`);
    await waitForApprovalResolution();
    approvalContainer.innerHTML = "";
    return;
  }

  const btnRow = document.createElement("div");
  btnRow.className = "approval-buttons";
  const approveBtn = document.createElement("button");
  approveBtn.textContent = "Approve";
  approveBtn.className = "approve-btn";
  const denyBtn = document.createElement("button");
  denyBtn.textContent = "Deny";
  denyBtn.className = "deny-btn";
  btnRow.appendChild(approveBtn);
  btnRow.appendChild(denyBtn);
  card.appendChild(btnRow);
  approvalContainer.appendChild(card);

  let resolved = false;
  const resolveApproval = async (approve) => {
    if (resolved) return;
    resolved = true;
    approveBtn.disabled = true;
    denyBtn.disabled = true;
    approvalContainer.innerHTML = "";
    const res = await apiFetch("/tools/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action_id: actionId, approve }),
    });
    await handleEventStream(res);
  };

  approveBtn.addEventListener("click", () => resolveApproval(true));
  denyBtn.addEventListener("click", () => resolveApproval(false));

  await speakText(`I'd like to ${description}. Say yes or no.`);
  if (resolved) return;
  const answer = await listenForSpeech(6000);
  if (resolved) return;
  setCaption(`You: ${answer || "(no answer heard)"}`);
  await resolveApproval(parseYesNo(answer));
}

/* ---------- admin: remote approval of OTHER sessions'/users' pending
 * requests (requires_admin ones) — polled separately from this browser's
 * own live /chat stream, since those requests never flow through it. ---------- */

let currentUser = null;

async function fetchCurrentUser() {
  try {
    const res = await apiFetch("/auth/me");
    currentUser = await res.json();
  } catch {
    currentUser = null;
  }
}

async function resolvePendingRemote(actionId, approve, cardEl) {
  cardEl.remove();
  try {
    const res = await apiFetch("/tools/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action_id: actionId, approve }),
    });
    // This drives resume_after_approval() to completion (it's a generator
    // consumed as the response streams out) but the outcome isn't narrated
    // here — the originating session picks it up via waitForApprovalResolution().
    if (res.body) {
      const reader = res.body.getReader();
      while (true) {
        const { done } = await reader.read();
        if (done) break;
      }
    }
  } catch {
    // best-effort
  }
  refreshPendingApprovals();
}

async function refreshPendingApprovals() {
  if (!currentUser || currentUser.role !== "admin") {
    adminPendingContainer.innerHTML = "";
    return;
  }
  try {
    const res = await apiFetch("/tools/pending");
    const data = await res.json();
    const others = (data.pending || []).filter((p) => p.requires_admin && p.session_id !== sessionId);

    adminPendingContainer.innerHTML = "";
    for (const p of others) {
      const card = document.createElement("div");
      card.className = "approval-card admin-approval-card";

      const label = document.createElement("div");
      label.className = "approval-label";
      label.textContent = `${p.requested_by} wants to ${p.tool}`;
      card.appendChild(label);

      const desc = document.createElement("div");
      desc.className = "approval-desc";
      desc.textContent = p.description;
      card.appendChild(desc);

      const btnRow = document.createElement("div");
      btnRow.className = "approval-buttons";
      const approveBtn = document.createElement("button");
      approveBtn.textContent = "Approve";
      approveBtn.className = "approve-btn";
      approveBtn.addEventListener("click", () => resolvePendingRemote(p.action_id, true, card));
      const denyBtn = document.createElement("button");
      denyBtn.textContent = "Deny";
      denyBtn.className = "deny-btn";
      denyBtn.addEventListener("click", () => resolvePendingRemote(p.action_id, false, card));
      btnRow.appendChild(approveBtn);
      btnRow.appendChild(denyBtn);
      card.appendChild(btnRow);

      adminPendingContainer.appendChild(card);
    }
  } catch {
    // transient — leave the last-rendered list in place
  }
}

/* ---------- reminders ---------- */

// The server marks a reminder "delivered" the moment /reminders/due
// returns it (see list_due_undelivered_reminders in core/memory/store.py)
// — so once fetched here, this is the ONLY chance to actually speak it. If
// the orb is mid-conversation this simply interrupts it, the same way a
// real ambient assistant would announce a timer rather than silently drop
// it; not worth a client-side queue for how rarely the two would overlap.
async function checkDueReminders() {
  try {
    const res = await apiFetch("/reminders/due");
    const data = await res.json();
    for (const reminder of data.due || []) {
      await speakText(`Reminder: ${reminder.text}`);
    }
  } catch {
    // transient — the next poll will pick up anything still due
  }
}

/* ---------- chat stream ---------- */

async function handleEventStream(res) {
  if (!res.ok || !res.body) {
    setCaption(`Error: ${res.status} ${res.statusText}`);
    setOrbState("idle");
    return;
  }

  setOrbState("thinking");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let full = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split("\n\n");
    buffer = events.pop();

    for (const evt of events) {
      const lines = evt.split("\n");
      const eventLine = lines.find((l) => l.startsWith("event:"));
      const dataLine = lines.find((l) => l.startsWith("data:"));
      if (!dataLine) continue;

      const eventType = eventLine ? eventLine.slice(6).trim() : "token";
      const payload = JSON.parse(dataLine.slice(5).trim());

      if (eventType === "token") {
        full += payload.token;
      } else if (eventType === "tool_call") {
        setCaption(`Running ${payload.tool}...`);
      } else if (eventType === "tool_denied") {
        setCaption(`${payload.tool} denied.`);
      } else if (eventType === "pending_action") {
        await handlePendingAction(
          payload.action_id,
          payload.tool,
          payload.args,
          payload.description,
          payload.requires_admin
        );
        return;
      } else if (eventType === "error") {
        setCaption(payload.message || "Unknown error");
      }
    }
  }

  if (full.trim()) {
    await speakText(full);
  } else {
    setOrbState("idle");
  }
}

async function sendToChat(text) {
  let res;
  try {
    res = await apiFetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    });
  } catch {
    setCaption("Could not reach Javi's server.");
    setOrbState("idle");
    return;
  }
  await handleEventStream(res);
}

/* ---------- boot ---------- */

async function checkHealth() {
  try {
    const res = await fetch("/health");
    const data = await res.json();
    statusDot.className = `dot ${data.ollama_connected ? "online" : "offline"}`;
    statusDot.title = data.ollama_connected ? `Connected — ${data.model}` : "Ollama not reachable";
    setOrbState(data.ollama_connected ? "idle" : "offline");
  } catch {
    statusDot.className = "dot offline";
    statusDot.title = "Server unreachable";
    setOrbState("offline");
  }
}

function showCameraFeed() {
  cameraPanel.hidden = false;
  // The MJPEG stream is a single never-ending response — only (re)point the
  // <img> at it when it isn't already connected, otherwise every 10s status
  // poll would tear down and reopen the connection. Checked via
  // getAttribute, not the `.src` property: once `.src` has been set to ""
  // (see hideCameraFeed), reading `.src` back resolves to the page's own
  // URL rather than an empty string, which would make this guard always
  // think a stream was already connected.
  if (!cameraFeedImg.getAttribute("src")) {
    cameraFeedImg.src = "/vision/camera/stream";
  }
}

function hideCameraFeed() {
  cameraPanel.hidden = true;
  cameraFeedImg.removeAttribute("src"); // actually closes the underlying stream connection
  cameraDetectionsList.textContent = "";
}

async function refreshCameraMonitorStatus() {
  try {
    const res = await apiFetch("/vision/camera/monitor/status");
    const data = await res.json();
    cameraMonitorDot.className = `dot ${data.active ? "active" : ""}`.trim();
    cameraMonitorDot.title = data.active
      ? `Camera monitoring: on (last capture ${data.last_capture_at || "pending"})`
      : "Camera monitoring: off";
    if (data.active) {
      showCameraFeed();
    } else {
      hideCameraFeed();
    }
    return data;
  } catch {
    cameraMonitorDot.className = "dot";
    cameraMonitorDot.title = "Camera monitoring: unknown (server unreachable)";
    hideCameraFeed();
    return null;
  }
}

async function refreshCameraDetections() {
  if (cameraPanel.hidden) return;
  try {
    const res = await apiFetch("/vision/camera/detections");
    const data = await res.json();
    const rows = data.detections || [];
    cameraDetectionsList.innerHTML = rows.length
      ? rows
          .map(
            (d) =>
              `<div class="detection-row">${d.label} <span class="track-id">#${d.track_id ?? "?"}</span> — ${Math.round(d.confidence * 100)}%</div>`
          )
          .join("")
      : `<div class="detection-row">Nothing detected right now</div>`;
  } catch {
    // transient — leave the last-rendered list in place
  }
}

cameraMonitorToggle.addEventListener("click", async () => {
  const status = await refreshCameraMonitorStatus();
  const endpoint = status && status.active ? "/vision/camera/monitor/stop" : "/vision/camera/monitor/start";
  await apiFetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
  await refreshCameraMonitorStatus();
});

async function boot() {
  await checkHealth();
  await fetchCurrentUser();
  await refreshPendingApprovals();
  await refreshCameraMonitorStatus();
  setInterval(refreshCameraMonitorStatus, 10000);
  setInterval(refreshCameraDetections, 1500);
  setInterval(refreshPendingApprovals, 3000);
  setInterval(checkDueReminders, 20000);
  const micReady = await initStandbyMic();
  if (micReady) {
    standbyLoop();
  }
}

boot();
