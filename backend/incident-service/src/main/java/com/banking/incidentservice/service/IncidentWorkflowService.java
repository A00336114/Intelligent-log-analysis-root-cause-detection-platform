package com.banking.incidentservice.service;

import com.banking.incidentservice.dto.IncidentUpdateRequest;
import com.banking.incidentservice.dto.IncidentWorkflowResponse;
import com.banking.incidentservice.dto.ParsedLogRequest;
import com.banking.incidentservice.dto.ParsedLogResponse;
import com.banking.incidentservice.model.Incident;
import com.banking.incidentservice.model.ParserStatus;
import com.banking.incidentservice.repository.IncidentRepository;
import com.fasterxml.jackson.databind.JsonNode;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class IncidentWorkflowService {

    private static final DateTimeFormatter SYNTHETIC_TIMESTAMP = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss");
    private static final Set<String> MANUAL_STATUSES = Set.of(
            "OPEN",
            "ACKNOWLEDGED",
            "RESOLVED",
            "FAILED"
    );

    private final IncidentRepository incidentRepository;
    private final LogParserClient logParserClient;
    private final AiEngineClient aiEngineClient;

    public IncidentWorkflowService(
            IncidentRepository incidentRepository,
            LogParserClient logParserClient,
            AiEngineClient aiEngineClient
    ) {
        this.incidentRepository = incidentRepository;
        this.logParserClient = logParserClient;
        this.aiEngineClient = aiEngineClient;
    }

    public IncidentWorkflowResponse createIncidentFromAlert(JsonNode payload) {
        NormalizedAlert alert = normalize(payload);

        Incident incident = new Incident();
        incident.setAlertName(alert.alertName());
        incident.setTitle(alert.alertName());
        incident.setDescription(alert.errorMessage());
        incident.setIncidentNumber(generateIncidentNumber(alert));
        incident.setServiceName(alert.serviceName());
        incident.setSeverity(alert.severity());
        incident.setStatus(normalizeIncidentStatus(alert.status()));
        incident.setSource(alert.source());
        incident.setRawPayload(payload.toString());
        incident.setRawLog(alert.rawLog());
        incident.setTraceId(alert.traceId());
        incident.setParserStatus(ParserStatus.PENDING);
        incident.setParserMessage("Incident saved and waiting for parser response");
        incident.setCreatedAt(alert.createdAt());
        incident.setUpdatedAt(alert.createdAt());

        incident = incidentRepository.save(incident);

        ParsedLogResponse parsedLog = null;

        try {
            parsedLog = logParserClient.parse(new ParsedLogRequest(
                    incident.getId(),
                    incident.getRawLog(),
                    incident.getServiceName(),
                    incident.getCreatedAt(),
                    alert.traceId(),
                    alert.statusCode(),
                    alert.failureType(),
                    alert.errorMessage()
            ));

            incident.setParserStatus(ParserStatus.COMPLETED);
            incident.setParserMessage("Parsed log stored successfully");
            incident.setParsedAt(LocalDateTime.now());
            incident.setUpdatedAt(LocalDateTime.now());

            if (hasText(parsedLog.traceId())) {
                incident.setTraceId(parsedLog.traceId());
            }

            incident = incidentRepository.save(incident);
            runAnomalyDetection(incident);
        } catch (Exception exception) {
            incident.setParserStatus(ParserStatus.FAILED);
            incident.setParserMessage("Log parser call failed: " + summarize(exception.getMessage()));
            incident.setUpdatedAt(LocalDateTime.now());
            incident = incidentRepository.save(incident);
        }

        return IncidentWorkflowResponse.from(incident, parsedLog);
    }

    private void runAnomalyDetection(Incident incident) {
        try {
            aiEngineClient.detectAnomaly(incident.getId());
        } catch (Exception exception) {
            incident.setParserMessage(
                    incident.getParserMessage() + "; anomaly detection pending: " + summarize(exception.getMessage())
            );
            incident.setUpdatedAt(LocalDateTime.now());
            incidentRepository.save(incident);
        }
    }

    public List<IncidentWorkflowResponse> getIncidents() {
        return incidentRepository.findAllByOrderByCreatedAtDesc()
                .stream()
                .map(incident -> IncidentWorkflowResponse.from(incident, null))
                .toList();
    }

    public IncidentWorkflowResponse getIncident(Long id) {
        Incident incident = incidentRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Incident not found"));
        return IncidentWorkflowResponse.from(incident, logParserClient.findByIncidentId(id));
    }

    public IncidentWorkflowResponse updateIncident(Long id, IncidentUpdateRequest request) {
        Incident incident = incidentRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Incident not found"));

        if (request != null && request.notes() != null) {
            incident.setNotes(hasText(request.notes()) ? request.notes().trim() : null);
        }

        if (request != null && hasText(request.status())) {
            incident.setStatus(normalizeManualStatus(request.status()));
        }

        LocalDateTime now = LocalDateTime.now();

        if (Boolean.TRUE.equals(request == null ? null : request.resolved())) {
            if (!isResolvedStatus(incident.getStatus())) {
                incident.setStatus("RESOLVED");
            }
            incident.setResolvedAt(now);
        } else if (isResolvedStatus(incident.getStatus())) {
            if (incident.getResolvedAt() == null) {
                incident.setResolvedAt(now);
            }
        } else if (request != null && (request.resolved() != null || hasText(request.status()))) {
            incident.setResolvedAt(null);
        }

        incident.setUpdatedAt(now);
        incident = incidentRepository.save(incident);

        return IncidentWorkflowResponse.from(incident, logParserClient.findByIncidentId(id));
    }

    private NormalizedAlert normalize(JsonNode payload) {
        JsonNode alertNode = firstAlert(payload);
        JsonNode resultNode = splunkResult(payload);

        String alertName = firstNonBlank(
                text(resultNode, "alertName"),
                text(payload, "alertName"),
                text(payload, "search_name"),
                nestedText(alertNode, "labels", "alertname"),
                nestedText(payload, "commonLabels", "alertname"),
                "PlatformIncident"
        );

        String serviceName = firstNonBlank(
                text(resultNode, "serviceName"),
                text(resultNode, "service_name"),
                text(payload, "serviceName"),
                nestedText(alertNode, "labels", "service_name"),
                nestedText(alertNode, "labels", "service"),
                nestedText(payload, "commonLabels", "service_name"),
                nestedText(payload, "commonLabels", "service"),
                "unknown-service"
        );

        String severity = firstNonBlank(
                text(resultNode, "severity"),
                severityFromLevel(text(resultNode, "level")),
                text(payload, "severity"),
                nestedText(alertNode, "labels", "severity"),
                nestedText(payload, "commonLabels", "severity"),
                "warning"
        );

        String status = firstNonBlank(
                text(resultNode, "status"),
                text(alertNode, "status"),
                text(payload, "status"),
                hasText(text(payload, "search_name")) ? "OPEN" : "firing"
        );

        String source = firstNonBlank(
                text(resultNode, "source"),
                text(payload, "source"),
                nestedText(alertNode, "labels", "source"),
                nestedText(payload, "commonLabels", "source"),
                hasText(text(payload, "search_name")) ? "splunk" : "grafana-webhook"
        );

        String traceId = firstNonBlank(
                text(resultNode, "traceId"),
                text(payload, "traceId"),
                text(payload, "sid"),
                nestedText(alertNode, "annotations", "traceId"),
                nestedText(payload, "commonAnnotations", "traceId"),
                nestedText(alertNode, "labels", "trace_id"),
                nestedText(payload, "commonLabels", "trace_id"),
                "incident-" + alertName.toLowerCase(Locale.ROOT).replace(' ', '-')
        );

        Integer statusCode = firstNonNull(
                integerValue(resultNode, "statusCode"),
                integerValue(payload, "statusCode"),
                nestedInteger(alertNode, "annotations", "statusCode"),
                nestedInteger(payload, "commonAnnotations", "statusCode"),
                nestedInteger(alertNode, "labels", "status_code"),
                nestedInteger(payload, "commonLabels", "status_code")
        );

        String failureType = firstNonBlank(
                text(resultNode, "failureType"),
                text(payload, "failureType"),
                nestedText(alertNode, "annotations", "failureType"),
                nestedText(payload, "commonAnnotations", "failureType"),
                nestedText(alertNode, "labels", "failure_type"),
                nestedText(payload, "commonLabels", "failure_type"),
                "APPLICATION_FAILURE"
        );

        String errorMessage = firstNonBlank(
                text(resultNode, "errorMessage"),
                text(resultNode, "message"),
                text(payload, "errorMessage"),
                nestedText(alertNode, "annotations", "description"),
                nestedText(payload, "commonAnnotations", "description"),
                nestedText(alertNode, "annotations", "summary"),
                nestedText(payload, "commonAnnotations", "summary"),
                alertName + " detected"
        );

        LocalDateTime createdAt = firstNonNull(
                parseDateTime(text(resultNode, "startsAt")),
                parseDateTime(text(resultNode, "timestamp")),
                parseDateTime(text(resultNode, "@timestamp")),
                parseDateTime(text(alertNode, "startsAt")),
                parseDateTime(text(payload, "startsAt")),
                LocalDateTime.now()
        );

        String rawLog = firstNonBlank(
                text(resultNode, "rawLog"),
                text(resultNode, "_raw"),
                text(payload, "rawLog"),
                nestedText(alertNode, "annotations", "rawLog"),
                nestedText(payload, "commonAnnotations", "rawLog"),
                nestedText(alertNode, "annotations", "log"),
                nestedText(payload, "commonAnnotations", "log"),
                synthesizeRawLog(createdAt, serviceName, severity, traceId, statusCode, failureType, errorMessage)
        );

        return new NormalizedAlert(
                alertName,
                serviceName,
                severity,
                status,
                source,
                rawLog,
                traceId,
                statusCode,
                failureType,
                errorMessage,
                createdAt
        );
    }

    private JsonNode firstAlert(JsonNode payload) {
        JsonNode alerts = payload.path("alerts");
        if (alerts.isArray() && !alerts.isEmpty()) {
            return alerts.get(0);
        }
        return payload;
    }

    private JsonNode splunkResult(JsonNode payload) {
        JsonNode resultNode = payload.path("result");
        if (resultNode.isObject()) {
            return resultNode;
        }
        return null;
    }

    private String synthesizeRawLog(
            LocalDateTime createdAt,
            String serviceName,
            String severity,
            String traceId,
            Integer statusCode,
            String failureType,
            String errorMessage
    ) {
        String level = "critical".equalsIgnoreCase(severity) || "error".equalsIgnoreCase(severity)
                ? "ERROR"
                : "WARN";
        String resolvedStatusCode = statusCode == null ? "500" : String.valueOf(statusCode);

        return "%s %s service=%s traceId=%s status=%s failure=%s java.lang.IllegalStateException: %s".formatted(
                createdAt.format(SYNTHETIC_TIMESTAMP),
                level,
                serviceName,
                traceId,
                resolvedStatusCode,
                failureType,
                errorMessage
        );
    }

    private String text(JsonNode node, String field) {
        if (node == null || node.isMissingNode() || node.isNull()) {
            return null;
        }

        JsonNode value = node.path(field);
        if (value.isMissingNode() || value.isNull()) {
            return null;
        }

        String textValue = value.asText();
        return hasText(textValue) ? textValue.trim() : null;
    }

    private String nestedText(JsonNode node, String objectField, String field) {
        if (node == null || node.isMissingNode() || node.isNull()) {
            return null;
        }

        JsonNode objectNode = node.path(objectField);
        if (!objectNode.isObject()) {
            return null;
        }

        JsonNode value = objectNode.path(field);
        if (value.isMissingNode() || value.isNull()) {
            return null;
        }

        String textValue = value.asText();
        return hasText(textValue) ? textValue.trim() : null;
    }

    private Integer integerValue(JsonNode node, String field) {
        return parseInteger(text(node, field));
    }

    private Integer nestedInteger(JsonNode node, String objectField, String field) {
        return parseInteger(nestedText(node, objectField, field));
    }

    private Integer parseInteger(String value) {
        if (!hasText(value)) {
            return null;
        }

        try {
            return Integer.valueOf(value.trim());
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private LocalDateTime parseDateTime(String value) {
        if (!hasText(value)) {
            return null;
        }

        try {
            return OffsetDateTime.parse(value).toLocalDateTime();
        } catch (DateTimeParseException ignored) {
        }

        try {
            return LocalDateTime.parse(value);
        } catch (DateTimeParseException ignored) {
        }

        try {
            return LocalDateTime.parse(value, DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        } catch (DateTimeParseException ignored) {
            return null;
        }
    }

    private String severityFromLevel(String level) {
        if (!hasText(level)) {
            return null;
        }

        String normalized = level.trim().toUpperCase(Locale.ROOT);
        return switch (normalized) {
            case "ERROR", "FATAL" -> "critical";
            case "WARN", "WARNING" -> "warning";
            case "INFO", "DEBUG", "TRACE" -> "info";
            default -> normalized.toLowerCase(Locale.ROOT);
        };
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (hasText(value)) {
                return value.trim();
            }
        }
        return null;
    }

    @SafeVarargs
    private final <T> T firstNonNull(T... values) {
        for (T value : values) {
            if (value != null) {
                return value;
            }
        }
        return null;
    }

    private boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    private String summarize(String value) {
        if (!hasText(value)) {
            return "No details returned";
        }
        return value.length() > 180 ? value.substring(0, 180) + "..." : value;
    }

    private String normalizeIncidentStatus(String status) {
        if (!hasText(status)) {
            return "OPEN";
        }

        String normalized = status.trim().toUpperCase(Locale.ROOT);
        return switch (normalized) {
            case "FIRING", "OPEN" -> "OPEN";
            case "ACKNOWLEDGED" -> "ACKNOWLEDGED";
            case "RESOLVED" -> "RESOLVED";
            case "FAILED" -> "FAILED";
            default -> "OPEN";
        };
    }

    private String normalizeManualStatus(String status) {
        String normalized = status.trim().toUpperCase(Locale.ROOT);
        if (!MANUAL_STATUSES.contains(normalized)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Unsupported incident status: " + status);
        }
        return normalized;
    }

    private boolean isResolvedStatus(String status) {
        if (!hasText(status)) {
            return false;
        }
        String normalized = status.trim().toUpperCase(Locale.ROOT);
        return "RESOLVED".equals(normalized) || "CLOSED".equals(normalized);
    }

    private String generateIncidentNumber(NormalizedAlert alert) {
        String prefix = alert.serviceName().replaceAll("[^A-Za-z0-9]", "").toUpperCase(Locale.ROOT);
        if (!hasText(prefix)) {
            prefix = "INC";
        }
        if (prefix.length() > 8) {
            prefix = prefix.substring(0, 8);
        }

        return prefix + "-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase(Locale.ROOT);
    }

    private record NormalizedAlert(
            String alertName,
            String serviceName,
            String severity,
            String status,
            String source,
            String rawLog,
            String traceId,
            Integer statusCode,
            String failureType,
            String errorMessage,
            LocalDateTime createdAt
    ) {
    }
}
