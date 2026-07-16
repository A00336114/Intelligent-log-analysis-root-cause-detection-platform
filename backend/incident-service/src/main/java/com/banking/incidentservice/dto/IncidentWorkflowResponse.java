package com.banking.incidentservice.dto;

import com.banking.incidentservice.model.Incident;
import com.banking.incidentservice.model.ParserStatus;
import java.time.LocalDateTime;

public record IncidentWorkflowResponse(
        Long id,
        String incidentNumber,
        String alertName,
        String serviceName,
        String severity,
        String status,
        String source,
        String rawLog,
        String traceId,
        ParserStatus parserStatus,
        String parserMessage,
        LocalDateTime createdAt,
        LocalDateTime updatedAt,
        LocalDateTime parsedAt,
        LocalDateTime resolvedAt,
        String notes,
        ParsedLogResponse parsedLog
) {

    public static IncidentWorkflowResponse from(Incident incident, ParsedLogResponse parsedLog) {
        return new IncidentWorkflowResponse(
                incident.getId(),
                incident.getIncidentNumber(),
                incident.getAlertName(),
                incident.getServiceName(),
                incident.getSeverity(),
                incident.getStatus(),
                incident.getSource(),
                incident.getRawLog(),
                incident.getTraceId(),
                incident.getParserStatus(),
                incident.getParserMessage(),
                incident.getCreatedAt(),
                incident.getUpdatedAt(),
                incident.getParsedAt(),
                incident.getResolvedAt(),
                incident.getNotes(),
                parsedLog
        );
    }
}
