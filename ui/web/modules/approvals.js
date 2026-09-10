function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const YES_WORDS = ["yes", "yeah", "yep", "sure", "go ahead", "approve", "confirm", "do it", "okay", "ok"];
const NO_WORDS = ["no", "nope", "don't", "do not", "stop", "cancel", "deny", "negative"];

function parseYesNo(text) {
  const t = text.toLowerCase();
  if (NO_WORDS.some((w) => t.includes(w))) return false;
  if (YES_WORDS.some((w) => t.includes(w))) return true;
  return false;
}

export function createApprovalsController({ ui, apiFetch, sessionId, getCurrentUser, speakText, listenForSpeech, isMuted }) {
  let handleEventStream = null;

  function setEventStreamHandler(handler) {
    handleEventStream = handler;
  }

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
            ui.setOrbState(isMuted() ? "muted" : "idle");
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
    ui.refs.approvalContainer.innerHTML = "";
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

    const currentUser = getCurrentUser();
    const isAdmin = !!(currentUser && currentUser.role === "admin");

    if (requiresAdmin && !isAdmin) {
      const waiting = document.createElement("div");
      waiting.className = "approval-waiting";
      waiting.textContent = "Waiting for an admin to approve this...";
      card.appendChild(waiting);
      ui.refs.approvalContainer.appendChild(card);

      ui.setOrbState("thinking");
      await speakText(`I need an admin to approve this: ${description}`);
      await waitForApprovalResolution();
      ui.refs.approvalContainer.innerHTML = "";
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
    ui.refs.approvalContainer.appendChild(card);

    let resolved = false;
    const resolveApproval = async (approve) => {
      if (resolved) return;
      resolved = true;
      approveBtn.disabled = true;
      denyBtn.disabled = true;
      ui.refs.approvalContainer.innerHTML = "";
      const res = await apiFetch("/tools/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action_id: actionId, approve }),
      });
      if (handleEventStream) {
        await handleEventStream(res);
      }
    };

    approveBtn.addEventListener("click", () => resolveApproval(true));
    denyBtn.addEventListener("click", () => resolveApproval(false));

    await speakText(`I'd like to ${description}. Say yes or no.`);
    if (resolved) return;
    const answer = await listenForSpeech(6000);
    if (resolved) return;
    ui.setCaption(`You: ${answer || "(no answer heard)"}`);
    await resolveApproval(parseYesNo(answer));
  }

  async function resolvePendingRemote(actionId, approve, cardEl) {
    cardEl.remove();
    try {
      const res = await apiFetch("/tools/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action_id: actionId, approve }),
      });
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
    const currentUser = getCurrentUser();
    if (!currentUser || currentUser.role !== "admin") {
      ui.refs.adminPendingContainer.innerHTML = "";
      return;
    }
    try {
      const res = await apiFetch("/tools/pending");
      const data = await res.json();
      const others = (data.pending || []).filter((p) => p.requires_admin && p.session_id !== sessionId);

      ui.refs.adminPendingContainer.innerHTML = "";
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

        ui.refs.adminPendingContainer.appendChild(card);
      }
    } catch {
      // transient — leave the last-rendered list in place
    }
  }

  return {
    setEventStreamHandler,
    handlePendingAction,
    refreshPendingApprovals,
  };
}
