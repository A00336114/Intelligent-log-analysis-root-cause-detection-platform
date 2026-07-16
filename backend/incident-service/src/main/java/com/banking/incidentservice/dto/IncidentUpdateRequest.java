package com.banking.incidentservice.dto;

public record IncidentUpdateRequest(
        String status,
        String notes,
        Boolean resolved
) {
}
