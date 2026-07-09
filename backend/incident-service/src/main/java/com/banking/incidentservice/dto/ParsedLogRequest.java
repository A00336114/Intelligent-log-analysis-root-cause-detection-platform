package com.banking.incidentservice.dto;

import java.time.LocalDateTime;

public record ParsedLogRequest(
        Long incidentId,
        String rawLog,
        String serviceName,
        LocalDateTime timestamp,
        String traceId,
        Integer statusCode,
        String failureType,
        String errorMessage
) {
}
