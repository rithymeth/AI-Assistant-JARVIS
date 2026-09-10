export function createChatController({ ui, apiFetch, sessionId, handlePendingAction, speakText }) {
  async function handleEventStream(res) {
    if (!res.ok || !res.body) {
      ui.setCaption(`Error: ${res.status} ${res.statusText}`);
      ui.setOrbState("idle");
      return;
    }

    ui.setOrbState("thinking");
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
          ui.setCaption(`Running ${payload.tool}...`);
        } else if (eventType === "tool_denied") {
          ui.setCaption(`${payload.tool} denied.`);
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
          ui.setCaption(payload.message || "Unknown error");
        }
      }
    }

    if (full.trim()) {
      await speakText(full);
    } else {
      ui.setOrbState("idle");
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
      ui.setCaption("Could not reach Javi's server.");
      ui.setOrbState("idle");
      return;
    }
    await handleEventStream(res);
  }

  return {
    handleEventStream,
    sendToChat,
  };
}
