# JARVIS — Local AI Assistant

A privacy-first, voice-controlled assistant for your computer. It reasons with a local Ollama model, can see the screen or webcam, and can operate the machine — with explicit approval gates for high-impact actions.

Internal code and the wake word still use **Javi**. The project name is **JARVIS**.

## What it does

- Local LLM + tool calling (Ollama)
- Voice wake word (`Javi` / `Hey Javi`), STT, TTS
- Screen and camera vision
- Web search and page fetch
- Notes, reminders, preferences
- Persistent memory (SQLite + ChromaDB)
- LAN / phone web UI with per-user access codes and optional face 2FA
- Approval-required actions: shell, unrestricted files, shutdown, automation, process kill

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com)
- Microphone (optional webcam)
- Windows 10/11 is the primary desktop-control target. Linux/macOS now have best-effort backends for open/list windows, volume, shutdown, Wi-Fi, and screenshots (`grim` / `gnome-screenshot` / `scrot` / `screencapture`).

## Install

```bash
git clone https://github.com/rithymeth/AI-Assistant-JARVIS.git
cd AI-Assistant-JARVIS
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Windows: copy .env.example .env
```

Windows-only packages (`pywin32`, `pycaw`, `pygetwindow`) are skipped automatically on Linux/macOS.

Optional `.env` knobs: `HOST`, `CAMERA_INDEX`, `WEATHER_LOCATION`, `ACCESS_CODE`.

Pull models:

```bash
ollama pull llama3.2:3b
ollama pull moondream
```

YOLOv8 nano weights (`yolov8n.pt`) are downloaded by Ultralytics on first camera detect if they are not already on disk. They are no longer committed to the repo.

## Run

Browser UI:

```bash
python main.py
```

Open http://localhost:8000 and allow the microphone.

Desktop WebView (this machine only):

```bash
python desktop.py
```

LAN bind is `HOST=0.0.0.0` by default. Stay local-only with:

```env
HOST=127.0.0.1
```

Do not run browser mode and desktop mode at the same time on the same port.

## Safety

The model is not the security boundary. Low-risk tools run immediately. High-impact tools pause until you approve them in the UI or by voice.

Do **not** expose an unrestricted instance to the public internet. LAN clients need an access code (auto-generated into `.access_code` unless you set `ACCESS_CODE`).

## Tests

```bash
python -m unittest discover -s tests -v
```

## Layout

```text
api/          FastAPI app
core/brain/   agent loop, policy, LLM client
core/memory/  SQLite + Chroma
tools/        web, files, PC, system, notes, weather
vision/       screen, camera, YOLO, OCR
voice/        STT / TTS
ui/web/       voice-first frontend
training/     optional LoRA experiments (not required at runtime)
```

## License

No open-source license is declared. Treat the repository as All Rights Reserved unless the owner adds one.

Author: [Rithy Meth](https://github.com/rithymeth)
