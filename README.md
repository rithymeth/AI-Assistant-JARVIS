# Javi — Voice-Only AI Assistant OS

A local, voice-only AI assistant that can see your screen, control your PC,
build up its own persistent knowledge from what it looks up, and answer
from your phone over WiFi — no chat log, no typing, no click to activate.
Just talk. Built in phases on top of a text-chat core, following the "small
working core → scale into agents → integrate capabilities" approach.

## Stack

- **Backend**: FastAPI + Ollama (`llama3.2:3b` by default), streamed
  responses, native Ollama tool-calling for the agent loop
- **Short-term memory**: SQLite (`javi.db`) — recent per-session chat history
- **Long-term memory**: ChromaDB + `sentence-transformers` embeddings
  (`chroma_data/`), two collections sharing one embedder/client
  (`core/memory/chroma_client.py`):
  - `javi_memories` — per-session conversation recall, beyond the recent window
  - `javi_knowledge` — global, cross-session facts Javi has looked up (web
    searches, page reads, screen looks, file reads) — this is Javi's actual
    "self-training": no model weights change, but what it has learned
    persists and gets recalled in future conversations regardless of session
- **PC control**: `pygetwindow` for window management, `pyautogui` for mouse
  /keyboard automation, `os.startfile` (ShellExecute) for opening apps/files
  /folders/URLs, sandboxed shell/file tools under `workspace/`
- **Web**: `duckduckgo-search` for search snippets, `requests` +
  `beautifulsoup4` (`fetch_page`) for reading a specific page's full text
- **Screen vision**: on-demand screenshot (`PIL.ImageGrab`) described by
  `moondream`, a small Ollama vision model — separate from the older
  YOLOv8 + `easyocr` pipeline used for uploaded-photo analysis
- **Voice**: `faster-whisper` (CPU) for speech-to-text, `pyttsx3` (Windows
  SAPI5) for text-to-speech — this *is* the interface, not an add-on.
  Standby listening uses client-side voice-activity detection (Web Audio
  API) to detect speech and silence, no click needed
- **Frontend**: plain HTML/CSS/JS, no build step — a single glowing orb,
  clock, and status line; no chat log or text input

## Setup

Requires [Ollama](https://ollama.com) installed and running locally, with two models pulled:

```bash
ollama pull llama3.2:3b
ollama pull moondream
```

Then:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

First run downloads a few small model weights automatically (YOLOv8n ~6MB,
the embedding model ~80MB) — after that everything runs fully offline. The
face-recognition second factor is the exception: `insightface`'s
`buffalo_l` model (~280MB) downloads on the *first* call to `embed_face()`
(i.e. the first `/auth/face/enroll` or `/auth/face/verify`, not at server
startup), cached under `~/.insightface/models/`. If you never enroll a
face, this download never happens.

## Run

**Web mode** (browser tab):

```bash
python main.py
```

Open [http://localhost:8000](http://localhost:8000) and allow microphone
access when prompted.

**Desktop mode** (native window, no browser chrome):

```bash
python desktop.py
```

Runs the same server internally and opens it in a real OS window via
`pywebview` (WebView2 on Windows) instead of a browser tab. Don't run both
at once — they'd fight over the same port.

**Autostart at login** (Windows): a Task Scheduler task named `Javi` runs
desktop mode automatically every time you log in — no console window, no
manual launch. Set up via:

```powershell
$action = New-ScheduledTaskAction -Execute "D:\Javis\.venv\Scripts\pythonw.exe" -Argument "D:\Javis\desktop.py" -WorkingDirectory "D:\Javis"
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 0)
Register-ScheduledTask -TaskName "Javi" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Launches Javi (voice assistant) desktop window at login"
```

To disable: `Unregister-ScheduledTask -TaskName "Javi"` in an elevated or
regular PowerShell prompt (no admin needed — it's a per-user task). To
check on it: `Get-ScheduledTaskInfo -TaskName "Javi"`.

Getting this working surfaced a real, fully diagnosed bug: the original
`.venv` (created via a `uv`-managed Python through a nested venv-creation
chain) had `.venv\Scripts\python.exe`/`pythonw.exe` launcher stubs that
worked fine when launched interactively (a terminal, `Start-Process` from
an active session) but failed under Task Scheduler's fresh-logon execution
context specifically — the launcher resolved a malformed redirect path
(`No Python at '"C:\...\pythonw.exe'`, note the stray leading quote) only
in that context, for reasons not fully root-caused (likely something
context-dependent in `uv`'s non-standard launcher stub, as opposed to
CPython's normal `pyvenv.cfg`-adjacency-based venv detection). Fixed by
recreating `.venv` from a standard system Python 3.10 install
(`python -m venv`, no `uv`, no nested chain) and reinstalling
`requirements.txt` into it — standard venv launchers don't have this
context-dependent failure. One unrelated wrinkle hit along the way: pip's
initial bulk install left a few small pure-Python packages
(`pygetwindow`, `pyautogui`, `proxy_tools` — all built from source rather
than a prebuilt wheel) incomplete/broken; reinstalling each individually
with `--no-cache-dir` fixed all three. Also bumped `onnxruntime` from
`1.28.0` to `1.23.2` in `requirements.txt` since `1.28.0` has no Python
3.10 wheel (verified insightface/face-recognition still works correctly
against 1.23.2). Verified end-to-end multiple times: real
`Start-ScheduledTask` trigger → server up within the (now 45s, previously
too-tight 15s) startup window → native window opens, correctly sized,
not minimized.

Either way: say **"Javi"** (or "Hey Javi") to talk to it — no click needed.
Standby listening is always on; it ignores speech that doesn't start with
the wake word, so it won't respond to ambient conversation. Click the orb
any time to mute/unmute standby listening.

**From your phone**, on the same WiFi: the startup banner (web mode only)
prints a URL — open it in your phone's browser. No app to install; it's
the same web UI.

**The access-code gate is enabled and per-user.** A phone or any other
device on the same WiFi/LAN needs a valid per-user access code
(`/auth/me`, `/auth/users` — see "Safety model" below for the full
mechanism, and multi-user auth under "What's left" for how this replaced
the original single shared code) to reach `/chat`, `/tools/`, `/history/`,
or `/auth/*`; the machine Javi runs on always has full (admin) access with
no code needed. A user can optionally enroll a face as an additional
second factor for LAN requests (`ui/web/enroll.html`, loopback-only) — see
"Face recognition as a second factor" below; nobody is required to.

There's also optional email-on-startup infrastructure (`core/notify.py`,
`SMTP_*`/`NOTIFY_EMAIL` in `.env.example`) built for emailing the access
code — currently unused since there's no code to send, but left in place
in case the gate comes back.

## Project layout

```
core/
  auth/
    users.py         # User dataclass, LOOPBACK_USER synthetic admin, per-user
                     # code generation + salted pbkdf2 hashing/verification
    face.py          # embed_face()/cosine_similarity() via insightface's
                     # FaceAnalysis(buffalo_l) — the second-factor face match
    face_sessions.py # opaque ~12h face-verification session tokens (in-memory)
  brain/      # LLM wrapper (text + vision chat), tool-calling agent loop, system prompt
  memory/
    store.py         # SQLite recent per-session chat history + `users`/`face_embeddings`/
                     # `preferences`/`reminders`/`notes` tables
    chroma_client.py # shared Chroma PersistentClient + embedder
    vector_store.py  # session-scoped conversation recall (javi_memories)
    knowledge.py      # global cross-session knowledge base (javi_knowledge)
tools/
  file_system.py  # read_file/write_file/list_dir, sandboxed to workspace/ (auto-exec
                  # for read_file/list_dir) + read_any_file/write_any_file/list_any_dir,
                  # unrestricted to any path on the machine — ALWAYS approval-gated
  shell.py        # run_command, sandboxed to workspace/ as cwd — ALWAYS approval-gated
  web_search.py, web_fetch.py  # search snippets + full-page-text fetch — auto-exec
  pc_control.py   # open_app (anything: apps/files/folders/URLs), close_app,
                  # focus_window, list_windows, take_screenshot — auto-exec
  automation.py   # click_at, type_text, press_key — ALWAYS approval-gated
  system_control.py  # set_volume, mute_volume, set_brightness, lock_screen,
                      # sleep_pc, shutdown_pc, restart_pc, toggle_wifi — ALWAYS
                      # approval-gated; cancel_shutdown — auto-exec (undoes a
                      # dangerous action, so gating it defeats its own purpose)
  process_control.py  # list_processes — auto-exec (read-only); kill_process —
                       # ALWAYS approval-gated, refuses a hardcoded set of
                       # OS-critical process names even when approved
  preferences.py  # remember_preference, recall_preferences, forget_preference —
                  # all auto-exec; standing corrections/instructions injected
                  # into EVERY conversation's context, unconditionally
  reminders.py  # set_reminder, list_reminders, cancel_reminder — all auto-exec;
                # date/time math (delay or next-occurrence-of-a-clock-time)
                # happens in Python, never asked of the small local model
  notes.py  # add_note, list_notes, remove_note, clear_list — all auto-exec;
            # named persistent lists (shopping, to-do, whatever the user
            # calls it) — plain content, distinct from preferences
            # (behavioral) and reminders (time-triggered)
  weather.py  # get_weather — auto-exec; Open-Meteo (free, no API key)
              # geocoding + current conditions/today's forecast
  worldclock.py  # get_time_in — auto-exec; same free geocoding (shared
                 # via _geo.py) + stdlib zoneinfo for the real DST-aware time
  _geo.py  # shared geocode()/format_place_name() helper for weather.py +
           # worldclock.py — not a tool itself, no registry.py entry
  system_status.py  # get_system_status — auto-exec; CPU/memory/every
                     # drive's disk usage/battery/uptime via psutil
vision/       # screen.py (on-demand screenshot description via moondream),
              # camera.py (on-demand webcam frame description) +
              # camera_monitor.py (toggleable background capture loop),
              # tracking.py (YOLO object detection + persistent-ID tracking)
              # + camera_stream.py (live MJPEG feed with boxes/labels/IDs
              # burned in, shown in ui/web's camera panel),
              # plus the older detection.py/ocr.py/describe.py photo pipeline
voice/        # speech-to-text (faster-whisper), text-to-speech (pyttsx3)
api/
  server.py   # FastAPI: /chat, /tools/approve, /tools/pending (admin-only),
              #          /auth/me, /auth/users (admin-only),
              #          /auth/face/enroll (loopback-only), /auth/face/verify,
              #          /reminders/due (marks-and-returns atomically),
              #          /vision/analyze, /vision/camera/monitor/{start,stop,status},
              #          /vision/camera/stream (live MJPEG), /vision/camera/detections,
              #          /voice/transcribe, /voice/speak, /history/{id}, /health
ui/web/       # voice-only HUD: orb (click to mute/unmute), clock, caption
              # line, approval-card fallback; standby VAD loop in app.js;
              # enroll.html — separate, minimal, loopback-only face-enrollment page
config/       # env-driven settings
workspace/    # sandbox directory file/shell tools operate in — nothing outside it is reachable
desktop.py    # native app shell (pywebview) — runs the same server + a real OS window
main.py       # web-mode entrypoint — same server, plain browser tab
training/     # isolated LoRA fine-tuning pipeline — zero shared code/deps
              # with the running app; see training/README.md
```

## Safety model

- **Auto-executes** (read-only or low-impact): `read_file`, `list_dir`,
  `web_search`, `fetch_page`, `open_app`, `close_app`, `focus_window`,
  `list_windows`, `describe_screen`, `describe_camera`, `list_processes`,
  `cancel_shutdown`.
- **Always pauses for approval, no exceptions**: `write_file`, `run_command`,
  `click_at`, `type_text`, `press_key`, `set_volume`, `mute_volume`,
  `set_brightness`, `lock_screen`, `sleep_pc`, `shutdown_pc`, `restart_pc`,
  `toggle_wifi`, `kill_process`, `read_any_file`, `write_any_file`,
  `list_any_dir`. Simulated clicks/keystrokes, shell commands, system-level
  changes, and anything reaching outside the workspace sandbox are all hard
  to undo, so this is a hard rule regardless of how "harmless" the specific
  action looks.
- **Full machine control, built on explicit request ("I want Javi to have
  full control if I told him to")** — the operative phrase being *if I told
  him to*: every one of these tools is approval-gated by the same mandatory
  mechanism above, no separate/weaker path. `tools/system_control.py` wraps
  `pycaw` (speaker volume/mute — the installed version exposes
  `AudioDevice.EndpointVolume` directly, no manual COM `Activate()` needed)
  and `screen_brightness_control` (display brightness), plus `lock_screen`
  (`user32.LockWorkStation`), `sleep_pc` (`powrprof.SetSuspendState`), and
  `shutdown_pc`/`restart_pc`/`cancel_shutdown` (wrap `shutdown.exe`, no
  `/f` force-flag — Windows' own unsaved-changes prompts in other apps
  still apply as a safety net on top of the approval gate).
  `shutdown_pc`/`restart_pc` take a `delay_seconds` (default 30) and can be
  undone with `cancel_shutdown` if called in time. `toggle_wifi` (via
  `netsh`) will surface a permissions error if Javi isn't running elevated
  — most Windows setups require admin for this, not tested with elevation
  here. `tools/process_control.py` adds `list_processes` (auto-exec,
  read-only, via `psutil`) and `kill_process` (by PID or a case-insensitive
  name substring, matching `close_app`'s window-matching UX) — `kill_process`
  refuses a small hardcoded set of OS-critical process names
  (`PROTECTED_PROCESS_NAMES`: `csrss.exe`, `wininit.exe`, `winlogon.exe`,
  `services.exe`, `lsass.exe`, `smss.exe`, `System`) even when approved,
  since killing those can bluescreen the machine outright with zero chance
  to undo it — the one case in this whole feature where approval alone
  isn't enough, same defense-in-depth reasoning as `open_app`'s
  shell-metacharacter rejection. `tools/file_system.py` adds
  `read_any_file`/`write_any_file`/`list_any_dir` — same operations as the
  sandboxed originals but resolving any real path on the machine, not just
  `workspace/`; distinct tool names rather than an "unrestricted mode" flag
  on the existing ones, so the sandboxed versions stay safely auto-exec and
  the risk is visible in which tool was called, not buried in an argument.
  Verified end-to-end through the real approval pipeline
  (`resume_after_approval`), not just unit-level: `list_processes` returns
  real running processes; an approved `set_volume` actually changes the
  system volume; a **denied** `shutdown_pc` is confirmed via `shutdown /a`
  to have genuinely never been scheduled at the OS level (not just "the
  Python function wasn't called" — asked Windows directly); `kill_process`
  correctly killed a disposable test process and correctly refused to kill
  `lsass.exe`; `read_any_file` correctly read a real file outside
  `workspace/`; a standard (non-admin) user's `shutdown_pc` request was
  correctly flagged `requires_admin` and their own attempt to approve it
  was rejected, mirroring the self-approval enforcement all approval-gated
  tools already had. `lock_screen`/`sleep_pc`/`toggle_wifi` specifically
  were implemented and code-reviewed but never fired for real during
  testing — each would have disrupted the actual live session (locking or
  sleeping the dev machine, or dropping WiFi) with no way to verify the
  result afterward, so unlike everything else in this project these are
  the one exception where "verified end-to-end" doesn't apply — try them
  yourself the first time.
- **Learns standing preferences/corrections, injected unconditionally into
  every conversation.** Distinct from `core/memory/knowledge.py`'s
  `javi_knowledge` (looked-up facts, semantically retrieved — used ONLY
  when relevant to the current message): `preferences` in
  `core/memory/store.py` are corrections and standing instructions ("call
  me X", "always"/"never" do Y, an explicit "remember this") that get
  included in FULL, every single turn, regardless of topic — the same
  unconditional treatment as `SYSTEM_PROMPT` itself, not a
  relevance-gated recall. `remember_preference`/`recall_preferences`/
  `forget_preference` (`tools/preferences.py`) are all auto-exec — storing
  or removing a line of remembered text isn't dangerous the way any of the
  PC-control tools above are, so gating it behind approval would just be
  friction with no real safety benefit. `SYSTEM_PROMPT` instructs the
  model to call `remember_preference` proactively — the user doesn't need
  to know the tool exists, just correct Javi or say "remember"/"always"/
  "never" naturally. Verified end-to-end through the real agent loop with
  the actual local model (not a mocked/simulated tool call): told it
  "Remember that you should always call me Captain" — it correctly called
  `remember_preference` and rephrased it into a clean standing instruction
  ("Always address the user as Captain") rather than storing the sentence
  verbatim; a completely unrelated next message ("What's 2+2?") was
  confirmed via direct inspection of the system prompt actually sent to
  the model to still include that preference in full; asking it to forget
  correctly called `forget_preference` and removed it. `MAX_INJECTED_PREFERENCES`
  caps this at the 30 most recent as a sanity bound, not expected to bite
  in normal use.
- **Reminders — "remind me in X" / "remind me at TIME," spoken aloud when
  due, no approval needed.** `tools/reminders.py`'s `set_reminder` takes
  the SIMPLEST possible inputs (`delay_minutes`, an integer, or `at_time`,
  a bare clock string like `"15:00"`/`"3:00 PM"`) and does all the actual
  date/time arithmetic in Python — `at_time` resolves to the next future
  occurrence of that clock time (today if it hasn't passed yet, otherwise
  tomorrow). Deliberately NOT asking the model to compute an absolute
  timestamp itself: small local models are unreliable at date/time
  arithmetic, a limitation already extensively documented elsewhere in
  this file. Delivery: `GET /reminders/due` (gated like `/history`)
  atomically marks-and-returns any reminder whose time has passed, within
  one SQLite transaction (`list_due_undelivered_reminders` in
  `core/memory/store.py`) — so a reminder fires exactly once even if
  polled from more than one client around the same moment, not a
  SELECT-then-UPDATE race across separate connections. `app.js` polls
  this every 20s and speaks each due reminder via the existing
  `speakText()`; reminders are global, not per-session/per-user (a
  single-household assistant's "remind me" naturally means "tell whoever's
  listening," not "only the tab that set it"). Verified end-to-end
  through the real HTTP endpoint (not just the store function): a
  non-loopback client without a code gets 401; a loopback client's first
  call after backdating a reminder's due time returns it; an immediate
  second call returns nothing, confirming exactly-once delivery through
  the actual gated endpoint. Also verified through the real agent loop
  with the real model: "remind me in 20 minutes to check the oven"
  correctly called `set_reminder`, and a later "what reminders do I have"
  correctly called `list_reminders` and relayed it back. Found a real gap
  along the way, documented honestly rather than glossed over:
  "cancel that oven reminder" sometimes didn't call `cancel_reminder` at
  all, and once called `forget_preference` instead — a genuine
  tool-selection miss consistent with this model's already-documented
  tool-use unreliability (see "llama3.2:3b's tool-use isn't fully
  reliable" below), not a bug in `cancel_reminder` itself, which works
  correctly whenever it IS actually called (verified directly, separately
  from the agent-loop test).
- **Named lists — shopping list, to-do list, whatever the user calls it —
  auto-exec, no approval needed.** `tools/notes.py`'s
  `add_note`/`list_notes`/`remove_note`/`clear_list`, backed by a `notes`
  table in `core/memory/store.py` (`list_name`, defaulting to `'general'`
  if the user doesn't name one, normalized case-insensitively so "Shopping"
  and "shopping" are the same list). Distinct from both other memory
  features above: not a behavioral instruction like a preference, not
  time-triggered like a reminder — just plain content the user wants
  tracked, recalled only when asked. Global, not per-session, for the same
  single-household reasoning as reminders. Verified through the real
  agent loop and turned up a genuinely useful, more specific finding than
  the tool-use unreliability already documented elsewhere: asking to "add
  milk to my shopping list" got a confident, fully-formed reply — *"I've
  added 'milk' to your shopping list"* — with **zero tool call underneath
  it** (confirmed directly by inspecting the actual conversation history
  in the database, not just the streamed events). A second message
  ("also add eggs") correctly called `add_note`. A third message ("what's
  on my list?") correctly called `list_notes` — which only ever had
  "eggs" in it — but the model's reply still confidently listed *both*
  "eggs" and "milk," because its own earlier fabricated claim about milk
  had become part of the conversation history it was reasoning from. Not
  a bug in `add_note`/`list_notes` (both verified working correctly in
  isolation) — a compounding failure mode worth having on record
  specifically because it's a step beyond the already-known "sometimes
  skips a tool call": a single skipped call's hallucinated success message
  went on to corrupt a *later, correctly-tooled* turn's answer too.
- **Weather — real current conditions and today's forecast, no API key
  needed.** `tools/weather.py` geocodes a city name and fetches weather
  from Open-Meteo (a genuinely free service, no signup/key/friction for
  the user — deliberately chosen over any provider that would require
  configuration before it could work at all). Auto-exec, like
  `web_search`. Metric units throughout (Celsius, km/h, mm), matching
  what this machine's own OS already shows. Optional `WEATHER_LOCATION`
  in `.env` covers "what's the weather" with no city named; if unset, the
  tool asks for a location rather than guessing one. Tool itself verified
  directly against the real live API for two real cities (Seattle, Tokyo)
  plus both error paths (unknown city name; no location and no default
  configured) — all correct. **The tool-selection story is the honest,
  important part of this entry**: through the real agent loop, the model
  failed to call `get_weather` in 4 out of 4 attempts across two different
  phrasings, instead fabricating a plausible-sounding non-answer or a
  fake "let me check the web" narration with zero underlying tool call.
  Tried strengthening `SYSTEM_PROMPT` with an explicit weather carve-out
  next to the existing "answer from your own knowledge" permission (the
  likely competing instruction) — still 0/2 after that change. Given
  `list_processes` and `add_note` both correctly triggered from natural
  phrasing in the same session right after, this isn't a general
  regression from adding a 40th tool — it's specific to weather, plausibly
  because small-talk weather questions are exactly the kind of thing this
  model has abundant non-tool-calling training signal for, unlike
  something like `kill_process` that has no plausible answer without a
  tool. Didn't keep hand-tuning the prompt indefinitely — that's what the
  LoRA pipeline in `training/` exists for. Instead, updated
  `training/data/synthetic_examples.jsonl`'s existing (now-outdated)
  Tokyo-weather example to demonstrate `get_weather` instead of the
  `web_search` workaround it was written against before this tool
  existed, and added two more real weather examples covering the
  no-location-given and casual-phrasing ("nice out today?") cases this
  session specifically reproduced.
- **World clock — real, DST-aware local time for a named city.**
  `tools/worldclock.py`'s `get_time_in` reuses the exact same free
  Open-Meteo geocoding call as `get_weather` (factored out into
  `tools/_geo.py` once a second tool needed it, rather than duplicating
  the request logic) — the geocoding response already includes each
  place's IANA timezone name directly, so the actual time computation is
  just stdlib `zoneinfo`, correctly DST-aware (verified directly: New
  York showed `-0400`/EDT and London `+0100`/BST in real August results,
  Tokyo `+0900` with no DST, all correct). `tzdata` (the IANA database
  `zoneinfo` needs on Windows, which doesn't ship it at the OS level) was
  already present only as a transitive dependency of `pandas` — pinned it
  explicitly in `requirements.txt` now that something imports it directly,
  same reasoning as `pywin32` earlier. Proactively added the same
  `SYSTEM_PROMPT` "you have no live clock" exception used for weather,
  learning from that investigation rather than waiting to rediscover the
  same problem — tool itself verified correct against real cities (Tokyo,
  New York, London) plus both error paths. Through the real agent loop,
  turned up a **different and specifically interesting** failure from
  weather's plain fabrication: for "what time is it in Tokyo," the model's
  reply was literally the text `Get_time_in("Tokyo")` — for "what's the
  time in London," it was *"I need to call get_time_in for that. Can I
  run that tool for you?"* Both show the model correctly identifying
  `get_time_in` by name as the right tool (the strengthened prompt did
  land) but failing to actually invoke Ollama's structured tool-calling
  interface, narrating its intent as conversational text instead — a
  materially different bug shape than weather's zero-tool-awareness
  fabrication, worth keeping distinct rather than lumping together. Ruled
  out a general regression the same way as before: `list_notes` correctly
  fired from natural phrasing in the same session. Added a new,
  more-specific `narrated_not_called` label (the existing failure-mode
  set didn't have one) to `training/data/synthetic_examples.jsonl` with
  two real examples covering both reproduced phrasings.
- **System status — real CPU/memory/every drive's disk usage/battery/
  uptime, via `psutil` (already a dependency, nothing new to install).**
  `tools/system_status.py`'s `get_system_status`. Reports every mounted
  drive (not just `C:`, since this machine alone has three), and omits
  `battery_percent`/`battery_plugged_in` entirely on hardware with no
  battery sensor at all rather than reporting a fake 0. Verified directly
  against this real machine's live state. This is the **third** "live PC
  state" tool built this session (after weather, world clock), and it
  fits the same now-well-established pattern: through the real agent
  loop, "how much battery do I have" got zero tool calls and a reply that
  literally fabricated a fake `get_system_status`-shaped output block
  with invented numbers; "how's my PC doing" called the wrong tool
  (`describe_screen`, which has nothing to do with resource stats) and
  *still* fabricated the actual numeric answer independent of that tool's
  real result. Ruled out a general regression the same way as the prior
  two investigations. Given three tools in a row show variations on the
  same "confidently answer live-state questions without properly using
  the tool" pattern, the fuller investigation write-ups are on the
  weather and world-clock entries above — this entry stays short rather
  than re-deriving the same conclusion a third time. Two more real
  examples (this time's exact fabricated-output and wrong-tool cases)
  added to `training/data/synthetic_examples.jsonl`.
- **Background training-data collection runs on its own, daily** — a
  Task Scheduler task (`JaviTrainingDataMiner`, registered the same way as
  the `Javi` autostart task) re-runs `training/scripts/mine_examples.py`
  once a day, so `training/data/needs_review.jsonl` keeps accumulating
  fresh candidate examples from real usage (including any corrections
  captured as preferences above, since those show up as real messages in
  `javi.db` the miner already scans) without you needing to remember to
  run it manually. It's still just candidate-flagging, never
  auto-training or auto-promoting anything into `train.jsonl` — see
  `training/README.md`'s existing caveats on why that mining is
  best-effort, not automatic ground truth. Verified directly: manually
  triggered the scheduled task and confirmed `needs_review.jsonl` was
  genuinely regenerated (35 real candidates from this project's own
  `javi.db` at time of writing) with a clean exit code, not just that the
  task registered successfully.
- **Voice-first approval**: when an action needs approval, Javi speaks what
  it wants to do and listens (until you go quiet — same voice-activity
  detection as standby listening) for a yes/no answer. Unclear or silent
  answers **fail closed** (treated as "no"). A clickable Approve/Deny card
  also renders as a fallback in case the mic/parsing doesn't cooperate —
  cheap redundancy for something this consequential.
- `open_app` rejects names containing shell metacharacters (`&`, `|`, `;`,
  newlines, etc.) before use, and calls `os.startfile` directly (ShellExecute
  — the same mechanism as double-clicking) rather than going through a shell
  at all, so classic shell-injection isn't even a applicable attack surface
  here — it auto-executes, so it still gets this defense-in-depth even
  though the realistic risk is model unreliability, not a malicious actor.
- `pyautogui.FAILSAFE` stays on — slamming the mouse to a screen corner
  aborts an in-flight automation call.
- **Access code gates LAN requests, not local ones — RE-ENABLED, now
  per-user.** (`GATED_PREFIXES = ("/chat", "/tools/", "/history/", "/auth/")`
  in `api/server.py`.) `main.py` has bound to `0.0.0.0` (LAN-reachable,
  subject to your Windows Firewall) since the very first version of this
  project — that wasn't new exposure introduced here, just
  previously-unprotected. Requests from the machine itself
  (`127.0.0.1`/`localhost`, matched via `ipaddress` parsing rather than an
  exact-string list — see below) skip the check entirely and resolve to a
  synthetic admin user (`core/auth/users.py`'s `LOOPBACK_USER`) — zero
  friction running Javi locally, in `desktop.py` or a browser tab, exactly
  as before; the person at the keyboard already had full control before any
  of this existed, that invariant doesn't change. Any other source IP (i.e.
  your phone, or anyone else on the WiFi) must send a matching
  `X-Javi-Access-Code` header on endpoints that take actions or reveal past
  content or identity (`/chat`, `/tools/`, `/history/*`, `/auth/*`) —
  `/health`, the static page, and `/voice/*`/`/vision/*` (audio/image I/O
  utilities, not actions) stay open so the page loads and standby listening
  doesn't need a code just to transcribe what it heard. Unlike the original
  single shared secret, the code now resolves to a specific user
  (`core/memory/store.py`'s `users` table: `username`, salted/hashed code,
  `role` of `admin` or `standard`) — real per-user identity, not just a
  pass/fail check. On first boot after this upgrade, if `users` is empty, a
  bootstrap admin is auto-created whose code is the pre-existing
  `ACCESS_CODE`/`.access_code` value, so a phone that already had the old
  code saved keeps working unchanged. Codes are drawn from an unambiguous
  alphabet (no `0`/`O`, `1`/`I`/`L`, no punctuation — the original version
  used `secrets.token_urlsafe`, which could generate a code starting with
  `-`, genuinely hard to transcribe by hand; fixed after a real report that
  a correctly-read code still wouldn't unlock) and compared case-insensitive
  (a phone keyboard's autocapitalize can't cause a false mismatch), hashed
  with `hashlib.pbkdf2_hmac` (200k iterations, per-user salt) before storage
  — never stored or logged in plaintext. Verified end-to-end (see
  "Multi-user auth" under "What's left" below, now built): a LAN request
  without a code or with a wrong code still gets 401; the right per-user
  code resolves that user's identity and role; localhost always gets
  through as admin with zero code.
- **Self-approval enforcement for standard users.** Every approval-gated
  tool call (`write_file`, `run_command`, `click_at`, `type_text`,
  `press_key`) records who requested it; if the requester isn't an admin,
  the request is flagged `requires_admin` and only an admin (or loopback)
  can resolve it — `core/brain/agent.py`'s `resume_after_approval` rejects
  a standard user trying to approve their own flagged request, even with a
  valid code. An admin sees other users' pending `requires_admin` requests
  via `GET /tools/pending` and can approve/deny them from an entirely
  different session/device; the requesting user's own session has no live
  connection to that approval (it happened on someone else's HTTP request),
  so it discovers the outcome by polling its own `/history/{session_id}`
  until the resulting assistant reply appears — the DB write always lands
  in the *original* requester's session regardless of who executed the
  approval. Verified end-to-end: a standard user's `write_file` request
  correctly becomes `requires_admin: true`; the standard user's own
  approve-attempt on it is rejected with no execution; an admin resolving
  it from a separate connection executes the tool and the resulting message
  lands in the original requester's session history.
- **Face recognition as a second factor on LAN requests, opt-in per user.**
  Layered strictly on top of the per-user access code, never a replacement
  for it — a user who never enrolls a face is entirely unaffected; one who
  does must pass both checks. `core/auth/face.py` wraps `insightface`'s
  `FaceAnalysis(name="buffalo_l")` (ONNX Runtime, CPU — same tradeoff as
  Voice STT below, no CUDA toolkit installed) to embed the largest
  sufficiently-confident face in a photo (512-d vector; detections below
  `MIN_DET_SCORE = 0.65` are discarded as noise — caught directly during
  calibration, when a real capture returned a second "face" at 0.59 that
  was clearly a shadow, not a face, on inspection) and compare it by cosine
  similarity against a user's enrolled embeddings
  (`core/memory/store.py`'s `face_embeddings` table, one or more per user —
  enrolling several angles/lighting conditions all count as a match).
  `FACE_MATCH_THRESHOLD = 0.35` was calibrated empirically, not guessed
  (same rigor as `SEMANTIC_DEDUP_DISTANCE`): two real webcam captures of the
  same person a few seconds apart scored ~0.69; a known different identity
  (insightface's own bundled `Tom_Hanks_54745.png` test asset) scored
  ~-0.08 against those same captures — the threshold sits with a wide
  margin below the same-person score (real verification photos, taken
  later under different lighting/pose, will likely score lower than that
  same-second pair) and a wide margin above the different-person score,
  biased conservative since this gates real control over the machine.
  **Enrollment is loopback-only, unconditionally** — `POST
  /auth/face/enroll` rejects any non-loopback caller with 403 via the
  existing `_is_loopback_host`, independent of and even if they supply a
  perfectly valid access code, since this is the step that decides whose
  face counts as a match; done from `ui/web/enroll.html`, a minimal page
  kept off the main voice UI. **Verification is session-scoped**: a LAN
  client that already passed the code check calls `POST
  /auth/face/verify` with a photo; on a match it gets an opaque ~12h token
  (`core/auth/face_sessions.py`, in-memory and ephemeral like
  `PENDING_ACTIONS`, bound to that specific user id) to send back as
  `X-Javi-Face-Session` on subsequent requests. `access_code_gate` in
  `api/server.py` checks `has_face_embeddings` for the code-resolved user
  and, only if true, additionally requires a valid session token for that
  same user id — a 401 with `reason: "face_verification_required"`
  distinguishes this from a plain bad-code 401 so `app.js`'s `apiFetch`
  knows to open the camera (`promptForFaceVerification()`, singleton for
  the same concurrent-caller reason as `promptForAccessCode()`) rather than
  show the code prompt. Verified end-to-end with real webcam captures: a
  LAN caller with a *valid* access code still gets 403 trying to enroll (not
  just an unauthenticated one); a code-holder with no enrolled face for
  their account is unaffected; an enrolled user's code alone (no face
  session) gets 401; a real *different* identity's photo (the Tom Hanks
  test asset) is correctly rejected despite the valid code — proving this
  is additive, not a second way to bypass the first factor; the enrolled
  person's own fresh photo succeeds and the resulting token unlocks
  subsequent requests; a wrong/bogus token, and a *different* enrolled
  user's face-session token presented against the first user's account,
  are both correctly rejected (tokens are bound to one specific user id).
- **The code-entry prompt is a singleton, not a footgun.** A second real
  bug report: standby listening retries `/voice/transcribe` on every
  detected sound, so before a code was entered, background retries kept
  calling the prompt function again — each call reset the input field back
  to empty and re-attached its own listeners, so a retry landing mid-typing
  (or right as you hit Unlock) silently wiped what you'd typed, and the
  click read an empty field and did nothing. Concurrent callers now share
  one pending prompt instead of each spawning a new one. Verified directly:
  fired three overlapping 401s, typed into the field, fired a fourth
  overlapping call mid-typing, confirmed the field still held what was
  typed, then confirmed one Unlock click resolved all four pending calls
  with the entered code. Combined with narrowing which endpoints are gated
  above, this should have been the actual fix for what was reported — it
  wasn't; the actual root cause was found next, from a screen recording
  the user sent showing the gate appearing in a real desktop Chrome window
  with the address bar literally reading `localhost:8000`, which should be
  architecturally impossible. The original loopback check compared
  `request.client.host` against a fixed set of three exact strings
  (`{"127.0.0.1", "::1", "localhost"}`) — but a loopback connection can
  legitimately arrive as other valid strings that set was never going to
  match (uncompressed IPv6 `"0:0:0:0:0:0:0:1"`, IPv4-mapped
  `"::ffff:127.0.0.1"`), and Windows networking can report any of these
  depending on the exact connection path a given browser takes. Replaced
  exact-string matching with `ipaddress` parsing plus an explicit
  IPv4-mapped unwrap, so any valid representation of a loopback address is
  recognized by what it *is*, not by whether it happens to match one of
  three hardcoded literals. Verified directly against all of the above
  forms plus real LAN addresses (correctly rejected) and a live end-to-end
  request via literal `localhost` (previously would have been the exact
  failure mode, now passes with no gate at all). The 401 response also now
  echoes back the exact `client_host` the server saw, so if this is
  somehow still wrong for a networking setup that wasn't covered, the next
  report comes with the answer already in it instead of needing a third
  round of guessing.
- **Email delivery of the code is best-effort and non-blocking** — if
  `SMTP_*`/`NOTIFY_EMAIL` aren't all set, or the send fails for any reason
  (wrong password, network hiccup, provider blocking it), the server logs
  why and starts normally regardless. It never gates startup on whether
  the email went out.

## Known limitations

- **Wake-word detection is transcribe-then-filter, not real-time keyword
  spotting.** There's no dedicated always-running wake-word model — every
  speech segment the VAD captures gets transcribed via the existing Whisper
  pipeline, THEN checked for "Javi"/"Jarvis" before anything is sent to the
  agent (`stripWakeWord` in `ui/web/app.js`). Costs an STT call either way,
  but means Javi only acts when addressed by name. Verified via unit-level
  and integration-level tests (extraction correctness, and the
  ignore/acknowledge/command branches all wired correctly) — but not
  against a real voice, since this environment has no microphone.
  The mic trigger threshold is now adaptive (an EMA-tracked ambient noise
  floor plus a fixed margin, calibrated on mic start and continuously
  updated during standby — see "adaptive noise floor" in `ui/web/app.js`)
  rather than one fixed constant, but its behavior on a real mic/room still
  couldn't be verified live here. Click the orb to mute if it's over- or
  under-triggering.
- **Desktop mode's rendering still wasn't visually confirmed — made a real
  second attempt this session, hit a genuine tooling wall.** `desktop.py`
  was re-verified to open a real native window (window enumeration
  confirms title "Javi", correct 480×780 size) and its embedded server
  responds correctly. This session tried actual screen-reading tools
  (computer-use) to go further: granting access by the window's owning
  process repeatedly resolved to the WRONG `python.exe` (two attempts, two
  different unrelated Python processes on this machine — a CLI tool's
  bundled interpreter, then a global install — never the actual project
  venv at `.venv\Scripts\python.exe` that owns the Javi window), so every
  screenshot masked the window out. Also noticed the window came up
  minimized when launched this way, but that's very likely an artifact of
  launching from a detached background shell process without Windows
  foreground-activation rights (a well-known OS behavior), not something a
  real user double-clicking the app would necessarily hit — not treating
  it as a confirmed bug without a way to test the normal launch path. It's
  still the identical HTML/CSS/JS already verified extensively in a normal
  browser, so it should render the same — take a look yourself the first
  time.
- **`open_app`'s documented first-call miss has a targeted fix applied, but
  the original failure couldn't be forced to reproduce for a true
  before/after comparison.** The hypothesized mechanism (`tools/pc_control.py`):
  `os.startfile`'s `ShellExecute` is COM-based, and FastAPI runs sync route
  handlers on threadpool worker threads — a freshly spun-up worker has
  never initialized a COM apartment on that thread, which can silently
  drop the first `ShellExecute` call. Fix applied: an explicit
  `pythoncom.CoInitialize()` before every `os.startfile` call (idempotent
  per-thread — a repeat call on an already-initialized thread is a no-op,
  verified directly: called twice on the same thread, second call raised
  nothing and still launched the app). What's honestly verified: 14
  fresh-process/fresh-thread trials (mimicking a brand-new FastAPI
  threadpool worker's very first call) all succeeded, both before and
  after the fix — meaning I could not force the original intermittent
  failure to reproduce in this session, so I can't claim a confirmed
  before/after fix, only that a real, low-cost, mechanistically-plausible
  fix is now in place for the exact failure mode previously documented. If
  "open X" ever silently does nothing on the very first try after starting
  Javi, that's still worth reporting — just ask again in the meantime.
- **Screen vision quality is genuinely mixed — worse than "confidently
  wrong" in one confirmed, reproducible case.** `moondream` is small
  (~1.7GB) and fast (~5s per description on this CPU-only machine), but on
  a busy, text-dense desktop screenshot it didn't just get details wrong —
  it broke into fully degenerate, incoherent output (`urn:ietf:wg:ac:200;`
  repeated hundreds of times on one run, `urn:focusviewer:1;urn:focusviewer:0`
  on another), reproduced 2/2 times on the same real screenshot. On a real
  (very dark) webcam frame it stayed coherent but fabricated specifics
  ("urn of water on table") that weren't in the actual image. Verified: the
  screenshot/photo capture itself is correct in both cases — checked the
  raw images directly — the model's description is what's unreliable.
  Directly compared against `llava:7b` (pulled and tested this session,
  already available via `ollama list` if you want it) on the same two real
  images: `llava:7b` never produced garbage output — it also got specifics
  wrong on the dark webcam frame (invented curtains, miscounted light
  sources) but always stayed coherent — at the cost of being ~5x slower
  (~26s vs ~5s per description here) and a bigger download (4.7GB vs
  1.7GB). Weighed that trade-off directly: kept `moondream` as the
  default since speed matters for a voice-first assistant and the
  degenerate-output case is specific to dense text/UI content, not typical
  usage — but if `describe_screen` answers matter more than latency for
  you, switch `VISION_MODEL_NAME=llava:7b` in `.env` (already pulled, no
  extra download needed). Treat `describe_screen`/`describe_camera`
  answers as a rough guess, not ground truth, either way.
- **The camera is one shared, persistent handle, not opened per call.**
  `tools/camera.py` opens the webcam once (lazily, on first use) and keeps it
  open behind a `threading.Lock`, rather than opening/closing per call — a
  live stream needs continuous access, and DirectShow (`cv2.CAP_DSHOW`)
  generally only allows one open handle to a webcam at a time on Windows, so
  every consumer (on-demand snapshot, background monitor, live MJPEG stream,
  object tracking) reads through the same `read_frame()` instead of each
  fighting for its own handle. Verified directly: triggered `describe_camera`
  via `/chat` while the live stream was actively pulling frames and confirmed
  no "device busy" exception, both just serialize instead of racing. Still a
  single hardcoded camera index (0) — multi-camera selection isn't supported.
- **Live tracking (`vision/tracking.py`) is real detection, not gimmick
  boxes — but it's `yolov8n` (the smallest YOLOv8 variant), so expect real
  false positives.** Verified directly via the actual `/vision/camera/stream`
  endpoint and the `/vision/camera/detections` JSON: a person in frame is
  correctly boxed and tracked with a stable ID across frames (confirmed the
  same `track_id` persists call-over-call), but low-confidence
  misclassifications from wall art/shadows (e.g. a picture frame briefly read
  as "cat" or "bed" at ~25-30% confidence) also show up. Treat anything under
  ~50% confidence as noise. Requires the `lap` package (Ultralytics'
  ByteTrack/BoT-SORT dependency for the linear-assignment step) —
  `pip install lap` if it's ever missing; it does NOT reliably auto-install
  itself into the right environment (verified: it auto-installed into the
  wrong, system-wide Python the first time, not this project's `.venv`).
  Streaming runs detection+tracking on every frame at a fixed ~8fps target —
  fine on this machine's RTX 3050, but a real, continuous GPU/CPU cost for as
  long as the camera panel is open, unlike the periodic (default 15s)
  background monitor.
- **`llama3.2:3b`'s tool-use isn't fully reliable.** It sometimes skips
  calling a tool and fabricates an answer instead, sometimes calls the right
  tool but then answers a different question than what was asked, sometimes
  re-fetches something already in its injected knowledge-base context
  instead of trusting it, and in long/busy conversations it can lose the
  thread entirely. The execution/approval *mechanics* are solid (verified
  directly — approval gates hold, denials block execution, sandboxing
  holds, knowledge persists and recalls correctly across sessions) even
  when the model's own reasoning about when/how to use them isn't. This
  shows up on `describe_camera` too — verified directly: asked "what do you
  see?" over `/chat`, it called `describe_camera` correctly and got back an
  accurate tool result, but then its spoken reply invented a bathroom, a
  window, and natural light that were never in the tool result or the actual
  photo. Not something new introduced by this feature, and left as-is here
  since fixing tool-use reliability itself is a separate, larger effort (see
  "What's left" below).
- **`web_search`** uses the free `duckduckgo-search` package (no API key) —
  it can hit rate limits under bursty use. `fetch_page` has no such limit
  (direct HTTP request) but obviously depends on the target site being up
  and not blocking simple scrapers.
- **Knowledge base curation handles the common cases, not all of them.**
  Each distinct lookup (tool + its exact args) upserts to a stable ID, so
  re-fetching the same page/query updates that one entry in place instead
  of duplicating. A *differently-phrased* lookup of the same underlying
  fact also merges, via vector-similarity dedup against existing entries
  (`SEMANTIC_DEDUP_DISTANCE` in `core/memory/knowledge.py`) — the threshold
  was calibrated empirically against this project's own embedder on
  realistic content (not guessed) and set conservatively: it reliably
  catches close paraphrases but deliberately won't try to catch every
  semantically-equivalent-but-differently-worded case, because the
  embedding signal wasn't clean enough to do that without risking two
  genuinely distinct facts silently merging into one. Recall also filters
  out anything older than 30 days (`DEFAULT_MAX_AGE_DAYS`). All three
  behaviors (exact-lookup dedup, paraphrase dedup, staleness expiry)
  verified directly with controlled test data — a paraphrased query
  correctly reused the existing entry, a genuinely distinct fact correctly
  got its own entry, and a simulated 90-day-old entry was correctly
  excluded at a 30-day cutoff but included at 120. What's NOT handled:
  active contradiction resolution beyond "the newest merged version wins."
- **Voice STT runs on CPU** — the GPU driver is present but the CUDA/cuBLAS
  toolkit isn't installed, so `faster-whisper` falls back to CPU (`base`
  model, still fast for short clips).
- **Phone access still isn't tested from an actual phone by me** — this
  environment has no physical device to confirm the real end-to-end
  experience. It has, however, been tried on a real phone by the user, who
  hit a real bug this way: the original code (`secrets.token_urlsafe`)
  could start with `-` and mix case in a way that a phone keyboard's
  autocapitalize would silently corrupt while typing, so a correctly-read
  code still wouldn't unlock. Fixed (unambiguous alphabet, no punctuation,
  case-insensitive comparison, autocapitalize/autocorrect/spellcheck
  disabled on the field) and re-verified — including deliberately sending
  the right code in the wrong case to prove the fix — but not yet
  re-confirmed on the actual phone that hit the original bug.
- **Email notification is untested with real credentials.** Verified the
  graceful-no-op path directly (missing config → clean skip, no crash,
  clear log line) — but actually sending mail needs a real SMTP account
  with a real password, which I have no way to obtain or should be handed
  in chat, so I could not confirm a live send. `SMTP_USER`/`NOTIFY_EMAIL`
  in `.env` are prefilled with your address as a sensible default;
  `SMTP_PASSWORD` is intentionally left blank for you to fill in yourself
  (a Gmail App Password, generated at
  https://myaccount.google.com/apppasswords — not your real password).

## What's left (not built)

Deliberately skipped, with reasons — not silently dropped:

- ~~Live camera feed~~ — **built.** The original reason (no camera in the
  build environment) no longer applied once this ran on a machine with a
  real "Integrated Camera": `vision/camera.py` (`describe_camera`, on-demand),
  `vision/camera_monitor.py` (toggleable background monitoring), plus a live
  view with object detection and per-object tracking IDs
  (`vision/tracking.py` + `vision/camera_stream.py`, shown in a camera panel
  in the web UI) — see the Safety model and Known limitations sections above.
- ~~Face recognition as an access method~~ — **built**, as a **second
  factor layered on top of the access code, never a replacement** — the
  original photo-spoofing concern (preserved below for context) applies to
  face-match *alone*, which is exactly why it was built as additive rather
  than as the only check. `core/auth/face.py` (embedding via
  `insightface`), `core/auth/face_sessions.py` (opaque ~12h tokens),
  `face_embeddings` table in `core/memory/store.py`, `POST
  /auth/face/enroll` + `POST /auth/face/verify` in `api/server.py`,
  `ui/web/enroll.html` (loopback-only enrollment page) and
  `promptForFaceVerification()` in `app.js`. See the Safety model section
  above for the full mechanism and empirical threshold calibration. Only
  applies to a user who has actually enrolled a face — everyone else is
  unaffected. Original concern, preserved for context: explicitly requested
  and declined at first, not just deferred for lack of hardware — a shared
  access code alone can't be spoofed by holding a photo up to a webcam;
  that's still true of the code by itself, which is why face-match was
  built strictly as an *additional* factor rather than a replacement for it.
- ~~Auth / multi-user support~~ — **built.** Real distinct accounts
  (`core/memory/store.py`'s `users` table: username, salted/hashed code,
  role) replace the single global `ACCESS_CODE`; `core/auth/users.py`
  handles code generation/hashing/verification, `core/brain/agent.py`
  enforces that a standard user can never self-approve their own
  approval-gated request (`requires_admin`, checked in
  `resume_after_approval`) — only an admin (including the always-trusted
  loopback synthetic admin) can resolve it, from any session. New endpoints:
  `GET /auth/me`, `GET/POST /auth/users` (admin-only), `GET /tools/pending`
  (admin-only, surfaces other users'/sessions' pending requests). See the
  Safety model section above for full detail and verification. Built before
  face-2FA below, as planned, so enrolled faces will attach to a real user
  from day one.
- **Actual model fine-tuning** — **pipeline scaffolded and code-complete,
  not yet trained.** Narrowly scoped to a LoRA/QLoRA adapter targeting the
  documented tool-use reliability problems (not personality/style), given
  the 4GB VRAM budget makes full fine-tuning a non-starter regardless. The
  full isolated pipeline lives in `training/` (see `training/README.md`):
  data mining from `javi.db` plus a hand-authored seed set, QLoRA training,
  CPU merge, GGUF conversion/quantization, and an Ollama `Modelfile` that
  pulls the live `SYSTEM_PROMPT` so it can't drift. `training/scripts/evaluate.py`
  already ran for real against baseline `llama3.2:3b` (no training needed for
  this part) and got **2/5** on the held-out failure-mode cases — confirming
  the 4 originally-documented problems plus a 5th (calling a tool for plain
  arithmetic/trivia) found directly during that run. What's blocking an
  actual trained model: the user's own HuggingFace license acceptance +
  token for the gated Llama 3.2 checkpoint, and a real WSL2 Ubuntu
  environment for the bitsandbytes/CUDA toolchain (checked directly — this
  machine's WSL2 only has Docker Desktop's internal distro) — both are
  one-time setup steps only the user can do, detailed in
  `training/README.md`. Since this was scoped: the data-collection half of
  this pipeline now runs on its own — see "Background training-data
  collection" under Safety model above — so `needs_review.jsonl` keeps
  growing with real candidates in the background regardless of when (or
  whether) the two blockers above get resolved.
- **Multi-agent collaboration** (planner/executor/critic) — `llama3.2:3b`
  already struggles with reliable single-agent tool use (extensively
  documented above); splitting into multiple coordinating agents would
  likely compound errors rather than fix them. Worth revisiting with a
  more capable model.

Three items above (camera feed, multi-user auth, face 2FA) are done; LoRA
fine-tuning is scaffolded and ready but not yet actually trained (blocked
on the user's own HF token + WSL2 setup — see `training/README.md`); multi-agent
collaboration remains untouched, out of scope for this revisit from the
start. Separately, mobile access turned out not to
need a dedicated mobile app at all: the existing web UI already works from
a phone browser over WiFi, gated by the (now per-user) access code
described above. A genuinely native mobile app (different framework, e.g.
Flutter, app-store distribution) would still be new scope if ever wanted,
but the "control Javi from your phone" need itself is covered.
