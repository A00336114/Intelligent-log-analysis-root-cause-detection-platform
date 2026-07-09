package com.banking.loggenerator.controller;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.banking.loggenerator.service.IncidentTestLogResult;
import com.banking.loggenerator.service.IncidentTestLogService;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(IncidentTestLogController.class)
class IncidentTestLogControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private IncidentTestLogService incidentTestLogService;

    @Test
    void patternsReturnsSupportedScenarios() throws Exception {
        when(incidentTestLogService.supportedScenarios())
                .thenReturn(List.of("PAYMENT_TIMEOUT", "DATABASE_FAILURE"));

        mockMvc.perform(get("/api/logs/incidents/patterns"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0]").value("PAYMENT_TIMEOUT"))
                .andExpect(jsonPath("$[1]").value("DATABASE_FAILURE"));
    }

    @Test
    void emitReturnsAcceptedResponse() throws Exception {
        when(incidentTestLogService.emit("PAYMENT_TIMEOUT"))
                .thenReturn(new IncidentTestLogResult("PAYMENT_TIMEOUT", "ERROR", "PAYMENT_TIMEOUT service=payment-service"));

        mockMvc.perform(post("/api/logs/incidents/PAYMENT_TIMEOUT"))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.scenario").value("PAYMENT_TIMEOUT"))
                .andExpect(jsonPath("$.level").value("ERROR"));

        verify(incidentTestLogService).emit("PAYMENT_TIMEOUT");
    }

    @Test
    void emitAllReturnsAcceptedResponse() throws Exception {
        when(incidentTestLogService.emitAll())
                .thenReturn(List.of(new IncidentTestLogResult("JAVA_EXCEPTION", "ERROR", "Exception while processing incident test batch")));

        mockMvc.perform(post("/api/logs/incidents/all"))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$[0].scenario").value("JAVA_EXCEPTION"));

        verify(incidentTestLogService).emitAll();
    }
}
