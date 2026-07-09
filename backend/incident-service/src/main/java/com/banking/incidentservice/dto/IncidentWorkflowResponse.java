package com.banking.incidentservice.dto;

import com.banking.incidentservice.model.Incident;
import com.banking.incidentservice.model.ParserStatus;
import java.time.LocalDateTime;

public record IncidentWorkflowResponse(
        Long id,
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
        LocalDateTime parsedAt,
        ParsedLogResponse parsedLog
) {

    public static IncidentWorkflowResponse from(Incident incident, ParsedLogResponse parsedLog) {
        return new IncidentWorkflowResponse(
                incident.getId(),
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
                incident.getParsedAt(),
                parsedLog
        );
    }
}
