package com.banking.incidentservice.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public record ParsedLogResponse(
        Long id,
        Long incidentId,
        String timestamp,
        String serviceName,
        String logLevel,
        String errorMessage,
        String exceptionType,
        Integer statusCode,
        String traceId,
        String failureType,
        String createdAt
) {
}
