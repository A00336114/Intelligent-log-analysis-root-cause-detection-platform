package com.banking.loggenerator.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class IncidentTestLogServiceTest {

    private IncidentTestLogService service;

    @BeforeEach
    void setUp() {
        service = new IncidentTestLogService();
    }

    @Test
    void supportedScenariosReturnsExpectedList() {
        assertThat(service.supportedScenarios()).containsExactly(
                "PAYMENT_TIMEOUT",
                "DATABASE_FAILURE",
                "LOGIN_FAILURE",
                "JAVA_EXCEPTION"
        );
    }

    @Test
    void emitReturnsExpectedMetadataForKnownScenario() {
        IncidentTestLogResult result = service.emit("PAYMENT_TIMEOUT");

        assertThat(result.scenario()).isEqualTo("PAYMENT_TIMEOUT");
        assertThat(result.level()).isEqualTo("ERROR");
        assertThat(result.message()).contains("PAYMENT_TIMEOUT");
    }

    @Test
    void emitAllReturnsAllScenarios() {
        List<IncidentTestLogResult> results = service.emitAll();

        assertThat(results).hasSize(4);
        assertThat(results).extracting(IncidentTestLogResult::scenario)
                .containsExactly("PAYMENT_TIMEOUT", "DATABASE_FAILURE", "LOGIN_FAILURE", "JAVA_EXCEPTION");
    }

    @Test
    void emitRejectsUnknownScenario() {
        assertThatThrownBy(() -> service.emit("UNKNOWN"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Unsupported scenario");
    }
}
