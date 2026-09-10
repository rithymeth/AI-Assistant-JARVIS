export function createCameraController({ ui, apiFetch }) {
  async function refreshCameraMonitorStatus() {
    try {
      const res = await apiFetch("/vision/camera/monitor/status");
      const data = await res.json();
      ui.setCameraMonitorState(
        !!data.active,
        data.active
          ? `Camera monitoring: on (last capture ${data.last_capture_at || "pending"})`
          : "Camera monitoring: off"
      );
      return data;
    } catch {
      ui.refs.cameraMonitorDot.className = "dot";
      ui.refs.cameraMonitorDot.title = "Camera monitoring: unknown (server unreachable)";
      ui.hideCameraFeed();
      return null;
    }
  }

  async function refreshCameraDetections() {
    if (ui.refs.cameraPanel.hidden) return;
    try {
      const res = await apiFetch("/vision/camera/detections");
      const data = await res.json();
      ui.renderDetections(data.detections || []);
    } catch {
      // transient — leave the last-rendered list in place
    }
  }

  function bindToggle() {
    ui.refs.cameraMonitorToggle.addEventListener("click", async () => {
      const status = await refreshCameraMonitorStatus();
      const endpoint = status && status.active ? "/vision/camera/monitor/stop" : "/vision/camera/monitor/start";
      await apiFetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      await refreshCameraMonitorStatus();
    });
  }

  return {
    refreshCameraMonitorStatus,
    refreshCameraDetections,
    bindToggle,
  };
}
