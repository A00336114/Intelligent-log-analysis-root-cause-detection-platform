package com.banking.loggenerator.service;

import java.util.List;
import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class IncidentTestLogService {

    private static final Logger log = LoggerFactory.getLogger(IncidentTestLogService.class);

    public List<IncidentTestLogResult> emitAll() {
        return List.of(
                emit("PAYMENT_TIMEOUT"),
                emit("DATABASE_FAILURE"),
                emit("LOGIN_FAILURE"),
                emit("JAVA_EXCEPTION")
        );
    }

    public IncidentTestLogResult emit(String scenario) {
        return switch (scenario) {
            case "PAYMENT_TIMEOUT" -> logError(
                    scenario,
                    "PAYMENT_TIMEOUT service=payment-service correlationId=" + shortId()
            );
            case "DATABASE_FAILURE" -> logError(
                    scenario,
                    "Connection refused while connecting to postgres correlationId=" + shortId()
            );
            case "LOGIN_FAILURE" -> logWarn(
                    scenario,
                    "LOGIN_FAILED username=incident-test-" + shortId()
            );
            case "JAVA_EXCEPTION" -> logException(
                    scenario,
                    "Exception while processing incident test batch correlationId=" + shortId()
            );
            default -> throw new IllegalArgumentException("Unsupported scenario: " + scenario);
        };
    }

    public List<String> supportedScenarios() {
        return List.of("PAYMENT_TIMEOUT", "DATABASE_FAILURE", "LOGIN_FAILURE", "JAVA_EXCEPTION");
    }

    private IncidentTestLogResult logError(String scenario, String message) {
        log.error(message);
        return new IncidentTestLogResult(scenario, "ERROR", message);
    }

    private IncidentTestLogResult logWarn(String scenario, String message) {
        log.warn(message);
        return new IncidentTestLogResult(scenario, "WARN", message);
    }

    private IncidentTestLogResult logException(String scenario, String message) {
        NullPointerException exception = new NullPointerException("Simulated incident test exception");
        log.error(message, exception);
        return new IncidentTestLogResult(scenario, "ERROR", message);
    }

    private String shortId() {
        return UUID.randomUUID().toString().substring(0, 8);
    }
}
