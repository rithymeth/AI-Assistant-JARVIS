const SESSION_KEY = "javi_session_id";
const ACCESS_CODE_KEY = "javi_access_code";
const FACE_SESSION_KEY = "javi_face_session";

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function createAuthController(ui) {
  let sessionId = localStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem(SESSION_KEY, sessionId);
  }

  let currentUser = null;
  let pendingAccessCodePrompt = null;
  let pendingFaceVerificationPrompt = null;

  function getStoredAccessCode() {
    return localStorage.getItem(ACCESS_CODE_KEY) || "";
  }

  function getStoredFaceSession() {
    return localStorage.getItem(FACE_SESSION_KEY) || "";
  }

  function promptForAccessCode() {
    if (pendingAccessCodePrompt) return pendingAccessCodePrompt;

    pendingAccessCodePrompt = new Promise((resolve) => {
      ui.refs.accessGateEl.hidden = false;
      ui.refs.accessCodeInput.value = "";
      ui.refs.accessCodeInput.focus();

      const onSubmit = () => {
        const code = ui.refs.accessCodeInput.value.trim();
        if (!code) return;
        localStorage.setItem(ACCESS_CODE_KEY, code);
        ui.refs.accessGateEl.hidden = true;
        ui.refs.accessCodeSubmit.removeEventListener("click", onSubmit);
        ui.refs.accessCodeInput.removeEventListener("keydown", onKeydown);
        pendingAccessCodePrompt = null;
        resolve(code);
      };
      const onKeydown = (e) => {
        if (e.key === "Enter") onSubmit();
      };

      ui.refs.accessCodeSubmit.addEventListener("click", onSubmit);
      ui.refs.accessCodeInput.addEventListener("keydown", onKeydown);
    });

    return pendingAccessCodePrompt;
  }

  async function captureFacePhoto() {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    try {
      const video = document.createElement("video");
      video.srcObject = stream;
      video.muted = true;
      await video.play();
      await sleep(400);
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
      return await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.9));
    } finally {
      stream.getTracks().forEach((t) => t.stop());
    }
  }

  function promptForFaceVerification() {
    if (pendingFaceVerificationPrompt) return pendingFaceVerificationPrompt;

    pendingFaceVerificationPrompt = (async () => {
      ui.setCaption("Face verification needed — look at the camera...");
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
          ui.setCaption("Face verification failed — try again.");
          return false;
        }
        const data = await res.json();
        localStorage.setItem(FACE_SESSION_KEY, data.face_session);
        ui.setCaption("Face verified.");
        return true;
      } catch {
        ui.setCaption("Couldn't access the camera for face verification.");
        return false;
      }
    })();

    const clear = () => {
      pendingFaceVerificationPrompt = null;
    };
    pendingFaceVerificationPrompt.then(clear, clear);
    return pendingFaceVerificationPrompt;
  }

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

  async function fetchCurrentUser() {
    try {
      const res = await apiFetch("/auth/me");
      currentUser = await res.json();
    } catch {
      currentUser = null;
    }
    return currentUser;
  }

  return {
    sessionId,
    apiFetch,
    fetchCurrentUser,
    getCurrentUser: () => currentUser,
  };
}
