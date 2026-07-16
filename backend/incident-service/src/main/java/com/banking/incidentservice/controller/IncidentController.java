package com.banking.incidentservice.controller;

import com.banking.incidentservice.dto.IncidentUpdateRequest;
import com.banking.incidentservice.dto.IncidentWorkflowResponse;
import com.banking.incidentservice.service.IncidentWorkflowService;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/incidents")
public class IncidentController {

    private final IncidentWorkflowService workflowService;

    public IncidentController(IncidentWorkflowService workflowService) {
        this.workflowService = workflowService;
    }

    @PostMapping("/alerts")
    public ResponseEntity<IncidentWorkflowResponse> receiveAlert(@RequestBody JsonNode payload) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(workflowService.createIncidentFromAlert(payload));
    }

    @GetMapping
    public ResponseEntity<List<IncidentWorkflowResponse>> getIncidents() {
        return ResponseEntity.ok(workflowService.getIncidents());
    }

    @GetMapping("/{id}")
    public ResponseEntity<IncidentWorkflowResponse> getIncident(@PathVariable Long id) {
        return ResponseEntity.ok(workflowService.getIncident(id));
    }

    @PutMapping("/{id}")
    public ResponseEntity<IncidentWorkflowResponse> updateIncident(
            @PathVariable Long id,
            @RequestBody IncidentUpdateRequest request
    ) {
        return ResponseEntity.ok(workflowService.updateIncident(id, request));
    }
}
