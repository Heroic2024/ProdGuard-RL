const taskSelect = document.getElementById("taskSelect");
const resetBtn = document.getElementById("resetBtn");
const refreshStateBtn = document.getElementById("refreshStateBtn");
const actionForm = document.getElementById("actionForm");
const actionSelect = document.getElementById("actionSelect");
const serviceInput = document.getElementById("serviceInput");
const causeInput = document.getElementById("causeInput");
const confidenceInput = document.getElementById("confidenceInput");
const stepBtn = document.getElementById("stepBtn");
const logsList = document.getElementById("logsList");
const metricsGrid = document.getElementById("metricsGrid");
const stepCount = document.getElementById("stepCount");
const lastReward = document.getElementById("lastReward");
const doneState = document.getElementById("doneState");
const finalScore = document.getElementById("finalScore");
const alertText = document.getElementById("alertText");
const responseBox = document.getElementById("responseBox");
const episodeStatus = document.getElementById("episodeStatus");

let currentState = null;
let latestDone = false;

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = body?.detail || `Request failed (${response.status})`;
    throw new Error(message);
  }

  return body;
}

function setStatus(text, mode) {
  episodeStatus.textContent = text;
  episodeStatus.className = "status-pill";
  if (mode) {
    episodeStatus.classList.add(mode);
  }
}

function pretty(obj) {
  return JSON.stringify(obj, null, 2);
}

function renderState(state, reward = null, done = null, info = null) {
  if (!state) {
    return;
  }

  currentState = state;
  stepCount.textContent = String(state.step_count ?? 0);
  alertText.textContent = state.alert || "No alert";

  if (typeof reward === "number") {
    lastReward.textContent = reward.toFixed(3);
  }

  if (typeof done === "boolean") {
    latestDone = done;
    doneState.textContent = done ? "Yes" : "No";
    setStatus(done ? "Episode Complete" : "Episode Running", done ? "done" : "running");
  }

  if (done && info && typeof info.score !== "undefined") {
    finalScore.textContent = String(info.score);
  }

  logsList.innerHTML = "";
  (state.visible_logs || []).forEach((line) => {
    const li = document.createElement("li");
    li.textContent = line;
    logsList.appendChild(li);
  });

  metricsGrid.innerHTML = "";
  const metrics = state.visible_metrics || {};
  Object.entries(metrics).forEach(([service, metric]) => {
    const card = document.createElement("div");
    card.className = "metric-row";

    const title = document.createElement("h4");
    title.textContent = service;
    card.appendChild(title);

    [
      ["CPU %", metric.cpu_pct],
      ["Memory %", metric.memory_pct],
      ["Error Rate", metric.error_rate],
      ["Latency ms", metric.latency_ms],
      ["RPS", metric.rps],
    ].forEach(([label, value]) => {
      const row = document.createElement("div");
      row.className = "metric-pair";
      const left = document.createElement("span");
      const right = document.createElement("span");
      left.textContent = label;
      right.textContent = String(value);
      row.appendChild(left);
      row.appendChild(right);
      card.appendChild(row);
    });

    metricsGrid.appendChild(card);
  });

  if (!state.visible_logs?.length) {
    logsList.innerHTML = "<li>No visible logs yet.</li>";
  }

  if (!Object.keys(metrics).length) {
    metricsGrid.innerHTML = "<div class='metric-row'>No visible metrics yet.</div>";
  }
}

function buildActionPayload() {
  const action = actionSelect.value;
  const payload = { action };

  const service = serviceInput.value.trim();
  const cause = causeInput.value.trim();
  const confidence = confidenceInput.value.trim();

  const serviceActions = new Set(["check_logs", "check_metrics", "restart_service", "scale_service"]);
  if (serviceActions.has(action) && service) {
    payload.service = service;
  }

  if (action === "declare_root_cause") {
    if (cause) {
      payload.cause = cause;
    }
    if (confidence !== "") {
      payload.confidence = Number(confidence);
    }
  }

  return payload;
}

function syncActionFieldHints() {
  const action = actionSelect.value;
  const needService = ["check_logs", "check_metrics", "restart_service", "scale_service"].includes(action);
  const needDiagnosis = action === "declare_root_cause";

  serviceInput.disabled = !needService;
  causeInput.disabled = !needDiagnosis;
  confidenceInput.disabled = !needDiagnosis;

  if (!needService) {
    serviceInput.value = "";
  }
  if (!needDiagnosis) {
    causeInput.value = "";
    confidenceInput.value = "";
  }
}

async function loadTasks() {
  const data = await api("/tasks", { method: "GET" });
  const tasks = data.tasks || [];
  taskSelect.innerHTML = "";
  tasks.forEach((task) => {
    const option = document.createElement("option");
    option.value = task;
    option.textContent = task;
    taskSelect.appendChild(option);
  });
  return tasks;
}

async function resetEpisode() {
  const task = taskSelect.value || "easy";
  const state = await api("/reset", {
    method: "POST",
    body: JSON.stringify({ task }),
  });
  finalScore.textContent = "-";
  doneState.textContent = "No";
  lastReward.textContent = "0.000";
  renderState(state, 0, false, null);
  responseBox.textContent = pretty({ reset: state });
}

async function refreshState() {
  const state = await api("/state", { method: "GET" });
  renderState(state, null, latestDone, null);
  responseBox.textContent = pretty({ state });
}

async function stepEpisode(payloadOverride = null) {
  const payload = payloadOverride || buildActionPayload();
  const result = await api("/step", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  renderState(result.state, Number(result.reward), Boolean(result.done), result.info);
  responseBox.textContent = pretty({ action: payload, result });
}

function bindEvents() {
  resetBtn.addEventListener("click", async () => {
    try {
      await resetEpisode();
    } catch (err) {
      responseBox.textContent = String(err);
      setStatus("Error", null);
    }
  });

  refreshStateBtn.addEventListener("click", async () => {
    try {
      await refreshState();
    } catch (err) {
      responseBox.textContent = String(err);
    }
  });

  actionSelect.addEventListener("change", syncActionFieldHints);

  actionForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!currentState) {
      responseBox.textContent = "Start an episode first.";
      return;
    }

    stepBtn.disabled = true;
    try {
      await stepEpisode();
    } catch (err) {
      responseBox.textContent = String(err);
    } finally {
      stepBtn.disabled = false;
    }
  });

  document.querySelectorAll("[data-qaction]").forEach((button) => {
    button.addEventListener("click", async () => {
      const action = button.getAttribute("data-qaction");
      const payload = { action };

      if (["check_logs", "check_metrics", "restart_service", "scale_service"].includes(action)) {
        payload.service = serviceInput.value.trim() || currentState?.services?.[0] || "";
      }

      try {
        await stepEpisode(payload);
      } catch (err) {
        responseBox.textContent = String(err);
      }
    });
  });
}

async function bootstrap() {
  setStatus("Loading", null);
  syncActionFieldHints();
  bindEvents();

  try {
    const tasks = await loadTasks();
    if (tasks.length > 0) {
      taskSelect.value = tasks[0];
    }
    await resetEpisode();
  } catch (err) {
    responseBox.textContent = String(err);
    setStatus("Backend Offline", null);
  }
}

bootstrap();
