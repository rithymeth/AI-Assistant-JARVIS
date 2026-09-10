import { createUIController } from "./modules/ui.js";
import { createAuthController } from "./modules/auth.js";
import { createVoiceController } from "./modules/voice.js";
import { createApprovalsController } from "./modules/approvals.js";
import { createChatController } from "./modules/chat.js";
import { createCameraController } from "./modules/camera.js";
import { createReminderController } from "./modules/reminders.js";

const ui = createUIController();
const auth = createAuthController(ui);
const voice = createVoiceController({ ui, apiFetch: auth.apiFetch });
const approvals = createApprovalsController({
  ui,
  apiFetch: auth.apiFetch,
  sessionId: auth.sessionId,
  getCurrentUser: auth.getCurrentUser,
  speakText: voice.speakText,
  listenForSpeech: voice.listenForSpeech,
  isMuted: voice.isMuted,
});
const chat = createChatController({
  ui,
  apiFetch: auth.apiFetch,
  sessionId: auth.sessionId,
  handlePendingAction: approvals.handlePendingAction,
  speakText: voice.speakText,
});
approvals.setEventStreamHandler(chat.handleEventStream);
const camera = createCameraController({ ui, apiFetch: auth.apiFetch });
const reminders = createReminderController({ apiFetch: auth.apiFetch, speakText: voice.speakText });

voice.bindOrbMuteToggle();
camera.bindToggle();
ui.startClock();

async function checkHealth() {
  try {
    const res = await fetch("/health");
    const data = await res.json();
    ui.setStatus(!!data.ollama_connected, data.ollama_connected ? `Connected — ${data.model}` : "Ollama not reachable");
  } catch {
    ui.setStatus(false, "Server unreachable");
  }
}

async function boot() {
  await checkHealth();
  await auth.fetchCurrentUser();
  await approvals.refreshPendingApprovals();
  await camera.refreshCameraMonitorStatus();
  setInterval(camera.refreshCameraMonitorStatus, 10000);
  setInterval(camera.refreshCameraDetections, 1500);
  setInterval(approvals.refreshPendingApprovals, 3000);
  setInterval(reminders.checkDueReminders, 20000);
  const micReady = await voice.initStandbyMic();
  if (micReady) {
    voice.standbyLoop(chat.sendToChat);
  }
}

boot();
