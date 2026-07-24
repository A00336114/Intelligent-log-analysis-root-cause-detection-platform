const state = {
  incidents: [],
  anomalies: [],
  recommendations: [],
  activeIncidentId: null,
  search: "",
  filter: "ALL",
};

const AI_ENGINE_BASE_URL = "http://localhost:8090";
const REQUEST_TIMEOUT_MS = 15000;
const INCIDENT_TABLE_COLUMN_COUNT = 8;
const IRELAND_TIMEZONE = "Europe/Dublin";
const IRELAND_DATE_FORMAT = new Intl.DateTimeFormat("en-IE", {
  timeZone: IRELAND_TIMEZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});
const IRELAND_DAY_FORMAT = new Intl.DateTimeFormat("en-CA", {
  timeZone: IRELAND_TIMEZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

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
  summaryAnomalies: document.querySelector("[data-summary-anomalies]"),
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
  detailAnomaly: document.querySelector("[data-detail-anomaly]"),
  detailRecommendation: document.querySelector("[data-detail-recommendation]"),
  recommendationGenerate: document.querySelector("[data-recommendation-generate]"),
  recommendationMessage: document.querySelector("[data-recommendation-message]"),
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
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const headers = { ...(options.headers || {}) };
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  try {
    const response = await fetch(url, { ...options, headers, signal: controller.signal });
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

    if (response.status === 204) {
      return null;
    }

    return response.json();
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error(`Request timed out after ${REQUEST_TIMEOUT_MS / 1000} seconds`);
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

function normalizeText(value) {
  return value == null ? "" : String(value).trim();
}

function formatDate(value) {
  if (!value) {
    return "Not available";
  }

  if (Array.isArray(value)) {
    const [year, month, day, hour = 0, minute = 0, second = 0] = value;
    return IRELAND_DATE_FORMAT.format(new Date(year, month - 1, day, hour, minute, second));
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }

  return IRELAND_DATE_FORMAT.format(parsed);
}

function getTimeValue(value) {
  if (!value) {
    return 0;
  }

  if (Array.isArray(value)) {
    const [year, month, day, hour = 0, minute = 0, second = 0] = value;
    return new Date(year, month - 1, day, hour, minute, second).getTime();
  }

  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? 0 : parsed.getTime();
}

function getIrelandDateKey(value) {
  const timeValue = getTimeValue(value);
  return timeValue ? IRELAND_DAY_FORMAT.format(new Date(timeValue)) : "";
}

function sortIncidentsNewestFirst(incidents) {
  return [...incidents].sort((left, right) => {
    const rightTime = getTimeValue(right.createdAt);
    const leftTime = getTimeValue(left.createdAt);

    if (rightTime !== leftTime) {
      return rightTime - leftTime;
    }

    return Number(right.id || 0) - Number(left.id || 0);
  });
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

function getAnomalyTone(anomaly) {
  if (!anomaly) {
    return "neutral";
  }
  return anomaly.isAnomaly || anomaly.is_anomaly ? "critical" : "healthy";
}

function getAnomalyLabel(anomaly) {
  if (!anomaly) {
    return "Not checked";
  }
  return anomaly.isAnomaly || anomaly.is_anomaly ? "Anomaly" : "Normal";
}

function getAnomalyScore(anomaly) {
  if (!anomaly) {
    return null;
  }
  const score = anomaly.anomalyScore ?? anomaly.anomaly_score;
  const parsed = typeof score === "number" ? score : Number(score);
  return Number.isFinite(parsed) ? parsed : null;
}

function getAnomalyForIncident(incidentId) {
  return state.anomalies.find((item) => Number(item.incidentId ?? item.incident_id) === Number(incidentId));
}

function getRecommendationForIncident(incidentId) {
  return state.recommendations.find((item) => Number(item.incidentId ?? item.incident_id) === Number(incidentId));
}

function setUpdateMessage(message, tone = "info") {
  elements.updateMessage.textContent = message || "";
  if (message) {
    elements.updateMessage.dataset.tone = tone;
  } else {
    delete elements.updateMessage.dataset.tone;
  }
}

function setRecommendationMessage(message, tone = "info") {
  elements.recommendationMessage.textContent = message || "";
  if (message) {
    elements.recommendationMessage.dataset.tone = tone;
  } else {
    delete elements.recommendationMessage.dataset.tone;
  }
}

function setUpdateControlsDisabled(disabled) {
  elements.updateStatus.disabled = disabled;
  elements.updateNotes.disabled = disabled;
  elements.updateSave.disabled = disabled;
  elements.updateResolve.disabled = disabled;
}

function updateSummary(incidents) {
  const openCount = incidents.filter((incident) => normalizeText(incident.status).toUpperCase() === "OPEN").length;
  const parsedCount = incidents.filter((incident) => normalizeText(incident.parserStatus).toUpperCase() === "COMPLETED").length;
  const failedCount = incidents.filter((incident) => normalizeText(incident.parserStatus).toUpperCase() === "FAILED").length;
  const anomalyCount = state.anomalies.filter((anomaly) => anomaly.isAnomaly || anomaly.is_anomaly).length;
  const criticalCount = incidents.filter((incident) => getSeverityTone(incident.severity) === "critical").length;
  const today = IRELAND_DAY_FORMAT.format(new Date());
  const newTodayCount = incidents.filter((incident) => getIrelandDateKey(incident.createdAt) === today).length;

  elements.summaryTotal.textContent = incidents.length;
  elements.summaryOpen.textContent = openCount;
  elements.summaryParsed.textContent = parsedCount;
  elements.summaryFailed.textContent = failedCount;
  elements.summaryAnomalies.textContent = anomalyCount;
  elements.summaryCritical.textContent = criticalCount;
  elements.summaryNew.textContent = newTodayCount;
}

function matchesFilter(incident) {
  if (state.filter === "ALL") {
    return true;
  }
  return normalizeText(incident.parserStatus).toUpperCase() === state.filter;
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
  return sortIncidentsNewestFirst(
    state.incidents.filter((incident) => matchesFilter(incident) && matchesSearch(incident))
  );
}

function getIncidentNumber(incident) {
  return incident.incidentNumber || `INC-${String(incident.id ?? 0).padStart(5, "0")}`;
}

function syncActiveSelection() {
  renderIncidentList();
}

function setActiveIncident(nextIncidentId) {
  state.activeIncidentId = nextIncidentId;
  renderIncidentList();
  if (nextIncidentId != null) {
    loadIncidentDetail(nextIncidentId).catch((error) => {
      if (Number(state.activeIncidentId) === Number(nextIncidentId)) {
        showDetailError(error);
      }
    });
  }
}

function renderIncidentList() {
  const visibleIncidents = getVisibleIncidents();
  const markup = visibleIncidents.length
    ? visibleIncidents
        .map((incident) => {
          const isActive = incident.id === state.activeIncidentId;
          const anomaly = getAnomalyForIncident(incident.id);
          const anomalyScore = getAnomalyScore(anomaly);
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
              <td>
                <span class="pill pill--${getAnomalyTone(anomaly)}">${escapeHtml(getAnomalyLabel(anomaly))}</span>
                ${anomalyScore == null ? "" : `<span>${escapeHtml(anomalyScore.toFixed(2))}</span>`}
              </td>
              <td>${escapeHtml(incident.traceId || "Not available")}</td>
            </tr>
          `;
        })
        .join("")
    : `
        <tr>
          <td colspan="${INCIDENT_TABLE_COLUMN_COUNT}">
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
  const anomaly = getAnomalyForIncident(incident.id);
  const anomalyScore = getAnomalyScore(anomaly);
  const recommendation = getRecommendationForIncident(incident.id);

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

  if (anomaly) {
    elements.detailAnomaly.innerHTML = [
      ["Status", getAnomalyLabel(anomaly)],
      ["Score", anomalyScore == null ? "Not available" : anomalyScore.toFixed(3)],
      ["Reason", anomaly.reason],
      ["Model", anomaly.modelVersion || anomaly.model_version || "Isolation Forest"],
      ["Updated", formatDate(anomaly.updatedAt || anomaly.updated_at)],
    ]
      .map(([label, value]) => `
        <div class="parsed-grid__item">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value ?? "Not available")}</strong>
        </div>
      `)
      .join("");
  } else {
    elements.detailAnomaly.innerHTML = `
      <div class="empty-inline">
        <strong>No anomaly result saved for this incident yet.</strong>
        <span>Refresh in a few seconds or check the analysis engine status.</span>
      </div>
    `;
  }

  renderRecommendation(recommendation);
}

function renderRecommendation(recommendation) {
  setRecommendationMessage("");
  elements.recommendationGenerate.disabled = state.activeIncidentId == null;

  if (!recommendation) {
    elements.detailRecommendation.innerHTML = `
      <div class="empty-inline">
        <strong>No recommendation saved for this incident yet.</strong>
        <span>Generate one to compare this incident with past notes and parsed logs.</span>
      </div>
    `;
    return;
  }

  const similarIncidents = recommendation.similarIncidents || recommendation.similar_incidents || [];
  const similarMarkup = similarIncidents.length
    ? `
      <div class="similar-list">
        ${similarIncidents.slice(0, 3).map((item) => `
          <div class="similar-item">
            <strong>${escapeHtml(item.incidentNumber || item.incident_number || `Incident ${item.incidentId || item.incident_id}`)}</strong>
            <span>${escapeHtml(item.serviceName || item.service_name || "unknown-service")} | Score ${escapeHtml(Number(item.similarityScore ?? item.similarity_score ?? 0).toFixed(2))}</span>
          </div>
        `).join("")}
      </div>
    `
    : recommendation.similarIncidentId != null || recommendation.similar_incident_id != null
      ? `
        <div class="similar-list">
          <div class="similar-item">
            <strong>Incident ${escapeHtml(recommendation.similarIncidentId ?? recommendation.similar_incident_id)}</strong>
            <span>Score ${escapeHtml(Number(recommendation.similarityScore ?? recommendation.similarity_score ?? 0).toFixed(2))}</span>
          </div>
        </div>
      `
      : "<p>No similar incident found.</p>";

  elements.detailRecommendation.innerHTML = `
    <div class="recommendation-block">
      <span>Likely root cause</span>
      <p>${escapeHtml(recommendation.recommendedRootCause || recommendation.recommended_root_cause)}</p>
    </div>
    <div class="recommendation-block">
      <span>Recommended fix</span>
      <p>${escapeHtml(recommendation.recommendedFix || recommendation.recommended_fix)}</p>
    </div>
    <div class="recommendation-block">
      <span>Evidence</span>
      <p>${escapeHtml(recommendation.evidence || "No evidence summary available.")}</p>
    </div>
    <div class="recommendation-block">
      <span>Similar past incidents</span>
      ${similarMarkup}
    </div>
    <div class="recommendation-block">
      <span>Model</span>
      <strong>${escapeHtml(recommendation.modelUsed || recommendation.model_used || "rules-and-similarity")}</strong>
    </div>
  `;
}

function showDetailError(error) {
  closeDetail();
  alert(`Unable to load incident detail: ${error.message || "Unexpected error"}`);
}

async function loadIncidentDetail(incidentId) {
  const incident = await requestJson(`/api/incidents/${incidentId}`);
  if (Number(state.activeIncidentId) !== Number(incidentId)) {
    return;
  }
  renderDetail(incident);
}

async function loadIncidents() {
  elements.refreshButton.disabled = true;
  elements.refreshButton.textContent = "Refreshing...";

  try {
    const [incidents, anomalies, recommendations] = await Promise.all([
      requestJson("/api/incidents"),
      loadAnomalyResults(),
      loadRecommendationResults(),
    ]);
    state.incidents = Array.isArray(incidents) ? incidents : [];
    state.anomalies = Array.isArray(anomalies) ? anomalies : [];
    state.recommendations = Array.isArray(recommendations) ? recommendations : [];
    elements.lastUpdated.textContent = `Updated ${formatDate(new Date())}`;
    updateSummary(state.incidents);
    renderIncidentList();
  } catch (error) {
    elements.incidentList.innerHTML = `
      <tr>
        <td colspan="${INCIDENT_TABLE_COLUMN_COUNT}">
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

async function loadAnomalyResults() {
  try {
    return await requestJson(`${AI_ENGINE_BASE_URL}/anomalies`) || [];
  } catch (error) {
    console.warn("Unable to load anomaly results", error);
    return [];
  }
}

async function loadRecommendationResults() {
  try {
    return await requestJson(`${AI_ENGINE_BASE_URL}/recommendations`) || [];
  } catch (error) {
    console.warn("Unable to load root cause recommendations", error);
    return [];
  }
}

async function generateRecommendation() {
  if (state.activeIncidentId == null) {
    return;
  }

  elements.recommendationGenerate.disabled = true;
  setRecommendationMessage("Generating recommendation...", "info");

  try {
    const recommendation = await requestJson(`${AI_ENGINE_BASE_URL}/recommendations/${state.activeIncidentId}`, {
      method: "POST",
    });
    const nextRecommendations = state.recommendations.filter(
      (item) => Number(item.incidentId ?? item.incident_id) !== Number(state.activeIncidentId)
    );
    state.recommendations = [recommendation, ...nextRecommendations];
    renderRecommendation(recommendation);
    setRecommendationMessage("Recommendation generated.", "success");
  } catch (error) {
    setRecommendationMessage(error.message || "Unable to generate recommendation.", "error");
  } finally {
    elements.recommendationGenerate.disabled = false;
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
    state.filter = normalizeText(button.dataset.filter).toUpperCase();
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

elements.recommendationGenerate.addEventListener("click", generateRecommendation);

loadIncidents();
