const state = {
  incidents: [],
  activeIncidentId: null,
  search: "",
  filter: "ALL",
};

const MANUAL_STATUSES = [
  "OPEN",
  "ACKNOWLEDGED",
  "RESOLVED",
  "FAILED",
];

const elements = {
  incidentList: document.querySelector("[data-incident-list]"),
  summaryTotal: document.querySelector("[data-summary-total]"),
  summaryOpen: document.querySelector("[data-summary-open]"),
  summaryParsed: document.querySelector("[data-summary-parsed]"),
  summaryFailed: document.querySelector("[data-summary-failed]"),
  summaryCritical: document.querySelector("[data-summary-critical]"),
  summaryNew: document.querySelector("[data-summary-new]"),
  lastUpdated: document.querySelector("[data-last-updated]"),
  searchInput: document.querySelector("[data-search-input]"),
  refreshButton: document.querySelector("[data-refresh-button]"),
  filterButtons: Array.from(document.querySelectorAll("[data-filter]")),
  detailTitle: document.querySelector("[data-detail-title]"),
  detailMeta: document.querySelector("[data-detail-meta]"),
  detailStatusPill: document.querySelector("[data-detail-status-pill]"),
  detailSeverityPill: document.querySelector("[data-detail-severity-pill]"),
  detailParserPill: document.querySelector("[data-detail-parser-pill]"),
  detailParserMessage: document.querySelector("[data-detail-parser-message]"),
  detailTimeline: document.querySelector("[data-detail-timeline]"),
  detailParsed: document.querySelector("[data-detail-parsed]"),
  detailRawLog: document.querySelector("[data-detail-raw-log]"),
  detailTrace: document.querySelector("[data-detail-trace]"),
  detailOverlay: document.querySelector("[data-detail-overlay]"),
  detailPanel: document.querySelector("[data-detail-panel]"),
  detailClose: document.querySelector("[data-detail-close]"),
  detailX: document.querySelector("[data-detail-x]"),
  updateForm: document.querySelector("[data-update-form]"),
  updateStatus: document.querySelector("[data-update-status]"),
  updateNotes: document.querySelector("[data-update-notes]"),
  updateSave: document.querySelector("[data-update-save]"),
  updateResolve: document.querySelector("[data-update-resolve]"),
  updateMessage: document.querySelector("[data-update-message]"),
};

async function requestJson(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    let detail = "";
    try {
      detail = await response.text();
    } catch (error) {
      detail = "";
    }

    const message = detail && detail.trim()
      ? `${response.status} ${detail.trim()}`
      : `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return response.json();
}

function normalizeText(value) {
  return typeof value === "string" ? value.trim() : "";
}

function formatDate(value) {
  if (!value) {
    return "Not available";
  }

  if (Array.isArray(value)) {
    const [year, month, day, hour = 0, minute = 0, second = 0] = value;
    return new Date(year, month - 1, day, hour, minute, second).toLocaleString();
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }

  return parsed.toLocaleString();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getSeverityTone(severity) {
  const normalized = normalizeText(severity).toUpperCase();
  if (normalized === "CRITICAL" || normalized === "HIGH" || normalized === "ERROR") {
    return "critical";
  }
  if (normalized === "WARNING" || normalized === "MEDIUM" || normalized === "WARN") {
    return "warning";
  }
  return "info";
}

function getParserTone(parserStatus) {
  const normalized = normalizeText(parserStatus).toUpperCase();
  if (normalized === "COMPLETED") {
    return "healthy";
  }
  if (normalized === "FAILED") {
    return "critical";
  }
  return "warning";
}

function getStatusTone(status) {
  const normalized = normalizeText(status).toUpperCase();
  if (normalized === "RESOLVED") {
    return "healthy";
  }
  if (normalized === "FAILED") {
    return "critical";
  }
  if (normalized === "ACKNOWLEDGED") {
    return "warning";
  }
  return "neutral";
}

function setUpdateMessage(message, tone = "info") {
  elements.updateMessage.textContent = message || "";
  if (message) {
    elements.updateMessage.dataset.tone = tone;
  } else {
    delete elements.updateMessage.dataset.tone;
  }
}

function setUpdateControlsDisabled(disabled) {
  elements.updateStatus.disabled = disabled;
  elements.updateNotes.disabled = disabled;
  elements.updateSave.disabled = disabled;
  elements.updateResolve.disabled = disabled;
}

function updateSummary(incidents) {
  const openCount = incidents.filter((incident) => normalizeText(incident.status) === "OPEN").length;
  const parsedCount = incidents.filter((incident) => normalizeText(incident.parserStatus) === "COMPLETED").length;
  const failedCount = incidents.filter((incident) => normalizeText(incident.parserStatus) === "FAILED").length;
  const criticalCount = incidents.filter((incident) => getSeverityTone(incident.severity) === "critical").length;
  const today = new Date().toDateString();
  const newTodayCount = incidents.filter((incident) => {
    const created = new Date(incident.createdAt);
    return !Number.isNaN(created.getTime()) && created.toDateString() === today;
  }).length;

  elements.summaryTotal.textContent = incidents.length;
  elements.summaryOpen.textContent = openCount;
  elements.summaryParsed.textContent = parsedCount;
  elements.summaryFailed.textContent = failedCount;
  elements.summaryCritical.textContent = criticalCount;
  elements.summaryNew.textContent = newTodayCount;
}

function matchesFilter(incident) {
  if (state.filter === "ALL") {
    return true;
  }
  return normalizeText(incident.parserStatus) === state.filter;
}

function matchesSearch(incident) {
  if (!state.search) {
    return true;
  }

  const haystack = [
    incident.alertName,
    incident.serviceName,
    incident.status,
    incident.severity,
    incident.traceId,
    incident.parserMessage,
    incident.rawLog,
    incident.notes,
  ]
    .map(normalizeText)
    .join(" ")
    .toLowerCase();

  return haystack.includes(state.search.toLowerCase());
}

function getVisibleIncidents() {
  return state.incidents.filter((incident) => matchesFilter(incident) && matchesSearch(incident));
}

function getIncidentNumber(incident) {
  return incident.incidentNumber || `INC-${String(incident.id).padStart(5, "0")}`;
}

function syncActiveSelection() {
  renderIncidentList();
}

function setActiveIncident(nextIncidentId) {
  state.activeIncidentId = nextIncidentId;
  renderIncidentList();
  if (nextIncidentId != null) {
    loadIncidentDetail(nextIncidentId).catch(showDetailError);
  }
}

function renderIncidentList() {
  const visibleIncidents = getVisibleIncidents();
  const markup = visibleIncidents.length
    ? visibleIncidents
        .map((incident) => {
          const isActive = incident.id === state.activeIncidentId;
          return `
            <tr class="${isActive ? "is-active" : ""}" data-incident-id="${incident.id}" tabindex="0">
              <td>
                <button class="incident-link" type="button" data-incident-id="${incident.id}">
                  ${escapeHtml(getIncidentNumber(incident))}
                </button>
                <span>${escapeHtml(incident.alertName || "Untitled incident")}</span>
              </td>
              <td>${escapeHtml(formatDate(incident.createdAt))}</td>
              <td>${escapeHtml(incident.serviceName || "unknown-service")}</td>
              <td><span class="pill pill--${getStatusTone(incident.status)}">${escapeHtml(incident.status || "OPEN")}</span></td>
              <td><span class="pill pill--${getSeverityTone(incident.severity)}">${escapeHtml(incident.severity || "unknown")}</span></td>
              <td><span class="pill pill--${getParserTone(incident.parserStatus)}">${escapeHtml(incident.parserStatus || "PENDING")}</span></td>
              <td>${escapeHtml(incident.traceId || "Not available")}</td>
            </tr>
          `;
        })
        .join("")
    : `
        <tr>
          <td colspan="7">
            <div class="empty-state">
              <h3>No incidents match this view</h3>
              <p>Try changing the parser filter or clearing the search field.</p>
            </div>
          </td>
        </tr>
      `;

  elements.incidentList.innerHTML = markup;

  elements.incidentList.querySelectorAll("tr[data-incident-id]").forEach((row) => {
    row.addEventListener("click", () => setActiveIncident(Number(row.dataset.incidentId)));
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        setActiveIncident(Number(row.dataset.incidentId));
      }
    });
  });
}

function closeDetail() {
  state.activeIncidentId = null;
  elements.detailOverlay.hidden = true;
  elements.detailPanel.hidden = true;
  renderIncidentList();
}

function renderDetail(incident) {
  elements.detailOverlay.hidden = false;
  elements.detailPanel.hidden = false;

  elements.detailTitle.textContent = incident.alertName || "Untitled incident";
  elements.detailMeta.textContent = `${incident.serviceName || "unknown-service"} | ${formatDate(incident.createdAt)}`;

  elements.detailStatusPill.className = `pill pill--${getStatusTone(incident.status)}`;
  elements.detailStatusPill.textContent = incident.status || "OPEN";

  elements.detailSeverityPill.className = `pill pill--${getSeverityTone(incident.severity)}`;
  elements.detailSeverityPill.textContent = incident.severity || "unknown";

  elements.detailParserPill.className = `pill pill--${getParserTone(incident.parserStatus)}`;
  elements.detailParserPill.textContent = incident.parserStatus || "PENDING";

  elements.detailParserMessage.textContent = incident.parserMessage || "No parser message available.";
  elements.detailTrace.textContent = incident.traceId || "Trace id not available";
  elements.detailRawLog.textContent = incident.rawLog || "Raw log not available";
  elements.updateStatus.value = MANUAL_STATUSES.includes(incident.status) ? incident.status : "OPEN";
  elements.updateNotes.value = incident.notes || "";
  setUpdateMessage("");

  elements.detailTimeline.innerHTML = [
    ["Created", formatDate(incident.createdAt)],
    ["Updated", formatDate(incident.updatedAt)],
    ["Parsed", formatDate(incident.parsedAt)],
    ["Resolved", formatDate(incident.resolvedAt)],
    ["Source", incident.source || "Unknown"],
  ]
    .map(([label, value]) => `
      <div class="detail-stat">
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(value)}</strong>
      </div>
    `)
    .join("");

  if (incident.parsedLog) {
    elements.detailParsed.innerHTML = [
      ["Timestamp", incident.parsedLog.timestamp],
      ["Log level", incident.parsedLog.logLevel],
      ["Exception", incident.parsedLog.exceptionType],
      ["Status code", incident.parsedLog.statusCode],
      ["Failure type", incident.parsedLog.failureType],
      ["Trace id", incident.parsedLog.traceId],
      ["Error message", incident.parsedLog.errorMessage],
    ]
      .map(([label, value]) => `
        <div class="parsed-grid__item">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value ?? "Not available")}</strong>
        </div>
      `)
      .join("");
  } else {
    elements.detailParsed.innerHTML = `
      <div class="empty-inline">
        <strong>Parsed log details are not available for this incident yet.</strong>
        <span>If the parser has just run, refresh once more in a few seconds.</span>
      </div>
    `;
  }
}

function showDetailError(error) {
  closeDetail();
  alert(`Unable to load incident detail: ${error.message || "Unexpected error"}`);
}

async function loadIncidentDetail(incidentId) {
  const incident = await requestJson(`/api/incidents/${incidentId}`);
  renderDetail(incident);
}

async function loadIncidents() {
  elements.refreshButton.disabled = true;
  elements.refreshButton.textContent = "Refreshing...";

  try {
    state.incidents = await requestJson("/api/incidents");
    elements.lastUpdated.textContent = `Updated ${new Date().toLocaleTimeString()}`;
    updateSummary(state.incidents);
    renderIncidentList();
  } catch (error) {
    elements.incidentList.innerHTML = `
      <tr>
        <td colspan="7">
          <div class="empty-state">
            <h3>Unable to load incidents</h3>
            <p>${escapeHtml(error.message || "Unexpected error")}</p>
          </div>
        </td>
      </tr>
    `;
  } finally {
    elements.refreshButton.disabled = false;
    elements.refreshButton.textContent = "Refresh";
  }
}

function mergeIncident(updatedIncident) {
  const nextIncidents = [...state.incidents];
  const index = nextIncidents.findIndex((incident) => incident.id === updatedIncident.id);

  if (index >= 0) {
    nextIncidents[index] = { ...nextIncidents[index], ...updatedIncident };
  } else {
    nextIncidents.unshift(updatedIncident);
  }

  state.incidents = nextIncidents;
  updateSummary(state.incidents);
  renderIncidentList();
  renderDetail(updatedIncident);
}

async function submitIncidentUpdate(options = {}) {
  if (state.activeIncidentId == null) {
    return;
  }

  const payload = {
    status: options.status || elements.updateStatus.value,
    notes: elements.updateNotes.value,
    resolved: Boolean(options.resolved),
  };

  setUpdateControlsDisabled(true);
  setUpdateMessage("Saving update...", "info");

  try {
    const updatedIncident = await requestJson(`/api/incidents/${state.activeIncidentId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    mergeIncident(updatedIncident);
    setUpdateMessage("Incident updated successfully.", "success");
  } catch (error) {
    setUpdateMessage(error.message || "Unable to save incident update.", "error");
  } finally {
    setUpdateControlsDisabled(false);
  }
}

elements.searchInput.addEventListener("input", (event) => {
  state.search = event.target.value.trim();
  syncActiveSelection();
});

elements.filterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.filter = button.dataset.filter;
    elements.filterButtons.forEach((item) => item.classList.toggle("is-selected", item === button));
    syncActiveSelection();
  });
});

elements.refreshButton.addEventListener("click", () => {
  loadIncidents();
});

elements.detailClose.addEventListener("click", closeDetail);
elements.detailX.addEventListener("click", closeDetail);
elements.detailOverlay.addEventListener("click", (event) => {
  if (event.target === elements.detailOverlay) {
    closeDetail();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !elements.detailOverlay.hidden) {
    closeDetail();
  }
});

elements.updateForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitIncidentUpdate();
});

elements.updateResolve.addEventListener("click", () => {
  submitIncidentUpdate({ status: "RESOLVED", resolved: true });
});

loadIncidents();
