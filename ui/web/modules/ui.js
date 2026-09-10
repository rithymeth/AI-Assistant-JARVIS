export function createUIController() {
  const refs = {
    statusDot: document.getElementById("status-dot"),
    cameraMonitorDot: document.getElementById("camera-monitor-dot"),
    cameraMonitorToggle: document.getElementById("camera-monitor-toggle"),
    cameraPanel: document.getElementById("camera-panel"),
    cameraFeedImg: document.getElementById("camera-feed-img"),
    cameraDetectionsList: document.getElementById("camera-detections-list"),
    orbEl: document.getElementById("jarvis-orb"),
    clockEl: document.getElementById("jarvis-clock"),
    stateEl: document.getElementById("jarvis-state"),
    captionEl: document.getElementById("jarvis-caption"),
    approvalContainer: document.getElementById("approval-container"),
    adminPendingContainer: document.getElementById("admin-pending-container"),
    accessGateEl: document.getElementById("access-gate"),
    accessCodeInput: document.getElementById("access-code-input"),
    accessCodeSubmit: document.getElementById("access-code-submit"),
  };

  const ORB_STATE_LABELS = {
    idle: "STANDBY",
    thinking: "PROCESSING",
    speaking: "SPEAKING",
    listening: "LISTENING",
    offline: "OFFLINE",
    muted: "MUTED",
  };

  let captionTimer = null;

  function setOrbState(state) {
    refs.orbEl.className = `jarvis-orb ${state === "idle" ? "" : state}`.trim();
    refs.stateEl.textContent = ORB_STATE_LABELS[state] || state.toUpperCase();
  }

  function startClock() {
    const tickClock = () => {
      const now = new Date();
      const hh = String(now.getHours()).padStart(2, "0");
      const mm = String(now.getMinutes()).padStart(2, "0");
      const ss = String(now.getSeconds()).padStart(2, "0");
      refs.clockEl.textContent = `${hh}:${mm}:${ss}`;
    };

    tickClock();
    setInterval(tickClock, 1000);
  }

  function setCaption(text) {
    refs.captionEl.textContent = text;
    refs.captionEl.classList.add("visible");
    if (captionTimer) clearTimeout(captionTimer);
    captionTimer = setTimeout(() => refs.captionEl.classList.remove("visible"), 8000);
  }

  function setStatus(online, title) {
    refs.statusDot.className = `dot ${online ? "online" : "offline"}`;
    refs.statusDot.title = title;
    setOrbState(online ? "idle" : "offline");
  }

  function showCameraFeed() {
    refs.cameraPanel.hidden = false;
    if (!refs.cameraFeedImg.getAttribute("src")) {
      refs.cameraFeedImg.src = "/vision/camera/stream";
    }
  }

  function hideCameraFeed() {
    refs.cameraPanel.hidden = true;
    refs.cameraFeedImg.removeAttribute("src");
    refs.cameraDetectionsList.textContent = "";
  }

  function setCameraMonitorState(active, title) {
    refs.cameraMonitorDot.className = `dot ${active ? "active" : ""}`.trim();
    refs.cameraMonitorDot.title = title;
    if (active) {
      showCameraFeed();
    } else {
      hideCameraFeed();
    }
  }

  function renderDetections(rows) {
    refs.cameraDetectionsList.innerHTML = rows.length
      ? rows
          .map(
            (d) =>
              `<div class="detection-row">${d.label} <span class="track-id">#${d.track_id ?? "?"}</span> — ${Math.round(d.confidence * 100)}%</div>`
          )
          .join("")
      : `<div class="detection-row">Nothing detected right now</div>`;
  }

  return {
    refs,
    setOrbState,
    startClock,
    setCaption,
    setStatus,
    showCameraFeed,
    hideCameraFeed,
    setCameraMonitorState,
    renderDetections,
  };
}
