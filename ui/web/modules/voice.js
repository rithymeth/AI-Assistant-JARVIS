const SILENCE_MS = 1200;
const MIN_SPEECH_MS = 300;
const MAX_RECORD_MS = 20000;
const WAKE_WORDS = ["hey javi", "hey jarvis", "javi", "jarvis"];
const NOISE_FLOOR_MARGIN = 0.015;
const MIN_THRESHOLD = 0.01;
const MAX_THRESHOLD = 0.2;
const NOISE_FLOOR_EMA_ALPHA = 0.05;
const CALIBRATION_MS = 800;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

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

export function createVoiceController({ ui, apiFetch }) {
  let micStream = null;
  let audioCtx = null;
  let analyser = null;
  let muted = false;
  let noiseFloor = 0.005;
  let voiceThreshold = MIN_THRESHOLD;

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

  function updateVoiceThreshold() {
    voiceThreshold = Math.min(MAX_THRESHOLD, Math.max(MIN_THRESHOLD, noiseFloor + NOISE_FLOOR_MARGIN));
  }

  function observeSilenceSample(vol) {
    noiseFloor += NOISE_FLOOR_EMA_ALPHA * (vol - noiseFloor);
    updateVoiceThreshold();
  }

  async function calibrateNoiseFloor(durationMs = CALIBRATION_MS) {
    const samples = [];
    const start = Date.now();
    while (Date.now() - start < durationMs) {
      samples.push(getVolume());
      await sleep(50);
    }
    if (samples.length) {
      samples.sort((a, b) => a - b);
      noiseFloor = samples[Math.floor(samples.length / 2)];
      updateVoiceThreshold();
    }
  }

  async function initStandbyMic() {
    try {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      ui.setCaption("Couldn't access the microphone — standby listening is unavailable.");
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
    ui.setOrbState("listening");

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
      ui.setOrbState(muted ? "muted" : "idle");
      return "";
    }
    ui.setOrbState("thinking");
    return transcribeBlob(new Blob(chunks, { type: "audio/webm" }));
  }

  function isBusy() {
    return (
      ui.refs.orbEl.className.includes("thinking") ||
      ui.refs.orbEl.className.includes("speaking") ||
      ui.refs.orbEl.className.includes("listening")
    );
  }

  async function speakText(text) {
    return new Promise((resolve) => {
      if (!text || !text.trim()) {
        resolve();
        return;
      }
      ui.setCaption(text);
      ui.setOrbState("speaking");
      (async () => {
        try {
          const res = await apiFetch("/voice/speak", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text }),
          });
          if (!res.ok) {
            ui.setOrbState("idle");
            resolve();
            return;
          }
          const blob = await res.blob();
          const audio = new Audio(URL.createObjectURL(blob));
          audio.addEventListener("ended", () => {
            ui.setOrbState("idle");
            resolve();
          });
          audio.addEventListener("error", () => {
            ui.setOrbState("idle");
            resolve();
          });
          audio.play();
        } catch {
          ui.setOrbState("idle");
          resolve();
        }
      })();
    });
  }

  async function standbyLoop(onCommand) {
    let lastDisplayed = null;
    while (true) {
      if (!micStream) {
        await sleep(1000);
        continue;
      }
      if (muted) {
        if (lastDisplayed !== "muted") {
          ui.setOrbState("muted");
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
        ui.setOrbState("idle");
        lastDisplayed = "idle";
      }

      const vol = getVolume();
      if (vol > voiceThreshold) {
        lastDisplayed = null;
        const text = await listenForSpeech();
        if (!text || !text.trim()) {
          ui.setOrbState(muted ? "muted" : "idle");
        } else {
          const command = stripWakeWord(text);
          if (command === null) {
            ui.setOrbState(muted ? "muted" : "idle");
          } else if (command === "") {
            await speakText("Yes?");
            const followUp = await listenForSpeech(8000);
            if (followUp && followUp.trim()) {
              ui.setCaption(`You: ${followUp}`);
              await onCommand(followUp);
            } else {
              ui.setOrbState(muted ? "muted" : "idle");
            }
          } else {
            ui.setCaption(`You: ${command}`);
            await onCommand(command);
          }
        }
      } else {
        observeSilenceSample(vol);
        await sleep(150);
      }
    }
  }

  function bindOrbMuteToggle() {
    ui.refs.orbEl.addEventListener("click", () => {
      muted = !muted;
      ui.setOrbState(muted ? "muted" : "idle");
      ui.setCaption(muted ? "Standby paused — click the orb to resume listening." : "Standby listening resumed.");
    });
  }

  return {
    initStandbyMic,
    listenForSpeech,
    speakText,
    standbyLoop,
    bindOrbMuteToggle,
    isMuted: () => muted,
  };
}
