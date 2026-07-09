package com.banking.loggenerator.controller;

import com.banking.loggenerator.service.IncidentTestLogResult;
import com.banking.loggenerator.service.IncidentTestLogService;
import java.util.List;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/logs/incidents")
public class IncidentTestLogController {

    private final IncidentTestLogService incidentTestLogService;

    public IncidentTestLogController(IncidentTestLogService incidentTestLogService) {
        this.incidentTestLogService = incidentTestLogService;
    }

    @GetMapping("/patterns")
    public List<String> patterns() {
        return incidentTestLogService.supportedScenarios();
    }

    @PostMapping("/{scenario}")
    public ResponseEntity<IncidentTestLogResult> emit(@PathVariable String scenario) {
        return ResponseEntity.accepted().body(incidentTestLogService.emit(scenario));
    }

    @PostMapping("/all")
    public ResponseEntity<List<IncidentTestLogResult>> emitAll() {
        return ResponseEntity.accepted().body(incidentTestLogService.emitAll());
    }
}
