const connectButton = document.getElementById("connect");
const disconnectButton = document.getElementById("disconnect");
const statusEl = document.getElementById("status");
const timerEl = document.getElementById("timer");
const videoEl = document.getElementById("video");
const serverUrlInput = document.getElementById("server-url");

let sessionId = null;
let sessionStatus = null;
let expiresAt = null;
let rtcPeer = null;
let controlSocket = null;
let statusPoll = null;
let timerInterval = null;
let listenersReady = false;

function setStatus(message) {
  statusEl.textContent = message;
}

function setTimer(message) {
  timerEl.textContent = message;
}

function getServerBase() {
  return serverUrlInput.value.replace(/\/$/, "");
}

function buildWebSocketUrl(path) {
  const base = getServerBase();
  const url = new URL(base);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = path;
  return url.toString();
}

async function joinSession() {
  const response = await fetch(`${getServerBase()}/api/session/join`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error("Failed to join session");
  }
  return response.json();
}

async function fetchStatus() {
  if (!sessionId) {
    return;
  }
  const response = await fetch(`${getServerBase()}/api/session/${sessionId}`);
  if (!response.ok) {
    return;
  }
  const data = await response.json();
  applySessionStatus(data);
}

function applySessionStatus(data) {
  sessionStatus = data.status;
  expiresAt = data.expires_at;
  if (sessionStatus === "controller") {
    setStatus("You are controlling the simulation.");
    if (!controlSocket) {
      openControlSocket();
    }
  } else if (sessionStatus === "queued") {
    const position = data.queue_position ?? "?";
    setStatus(`You are in the queue. Position: ${position}.`);
  } else if (sessionStatus === "expired") {
    setStatus("Your control slot expired. Reconnect to join the queue.");
    closeControlSocket();
  } else {
    setStatus("Session ready.");
  }
}

async function startWebRTC() {
  rtcPeer = new RTCPeerConnection();
  rtcPeer.addTransceiver("video", { direction: "recvonly" });
  rtcPeer.ontrack = (event) => {
    const [stream] = event.streams;
    if (stream) {
      videoEl.srcObject = stream;
    }
  };

  const offer = await rtcPeer.createOffer();
  await rtcPeer.setLocalDescription(offer);

  const response = await fetch(`${getServerBase()}/api/webrtc/offer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sdp: rtcPeer.localDescription.sdp,
      type: rtcPeer.localDescription.type,
      session_id: sessionId,
    }),
  });
  if (!response.ok) {
    throw new Error("Failed to negotiate WebRTC");
  }
  const answer = await response.json();
  await rtcPeer.setRemoteDescription(answer);
}

function openControlSocket() {
  controlSocket = new WebSocket(buildWebSocketUrl(`/api/control/${sessionId}`));
  controlSocket.onclose = () => {
    controlSocket = null;
  };
}

function closeControlSocket() {
  if (controlSocket) {
    controlSocket.close();
    controlSocket = null;
  }
}

function sendControl(payload) {
  if (!controlSocket || controlSocket.readyState !== WebSocket.OPEN) {
    return;
  }
  controlSocket.send(JSON.stringify(payload));
}

function setupInputListeners() {
  if (listenersReady) {
    return;
  }
  window.addEventListener("keydown", (event) => {
    if (sessionStatus !== "controller") {
      return;
    }
    sendControl({ type: "keydown", key: event.key, code: event.code });
  });

  videoEl.addEventListener("mousemove", (event) => {
    if (sessionStatus !== "controller") {
      return;
    }
    const rect = videoEl.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    sendControl({ type: "mousemove", x, y });
  });

  videoEl.addEventListener("mousedown", (event) => {
    if (sessionStatus !== "controller") {
      return;
    }
    sendControl({ type: "mousedown", button: event.button });
  });

  listenersReady = true;
}

function startTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
  }
  timerInterval = setInterval(() => {
    if (!expiresAt) {
      setTimer("");
      return;
    }
    const remainingMs = Math.max(0, expiresAt * 1000 - Date.now());
    const seconds = Math.ceil(remainingMs / 1000);
    setTimer(`Time remaining: ${seconds}s`);
  }, 500);
}

function resetUI() {
  sessionId = null;
  sessionStatus = null;
  expiresAt = null;
  setStatus("Not connected");
  setTimer("");
  videoEl.srcObject = null;
}

async function connect() {
  connectButton.disabled = true;
  try {
    const data = await joinSession();
    sessionId = data.session_id;
    applySessionStatus(data);
    await startWebRTC();
    setupInputListeners();
    statusPoll = setInterval(fetchStatus, 3000);
    startTimer();
    disconnectButton.disabled = false;
  } catch (error) {
    setStatus("Failed to connect. Check the server URL and try again.");
    console.error(error);
  } finally {
    connectButton.disabled = false;
  }
}

function disconnect() {
  if (statusPoll) {
    clearInterval(statusPoll);
    statusPoll = null;
  }
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
  closeControlSocket();
  if (rtcPeer) {
    rtcPeer.close();
    rtcPeer = null;
  }
  disconnectButton.disabled = true;
  resetUI();
}

connectButton.addEventListener("click", connect);

disconnectButton.addEventListener("click", disconnect);

resetUI();
