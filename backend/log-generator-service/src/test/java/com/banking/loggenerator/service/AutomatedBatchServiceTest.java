package com.banking.loggenerator.service;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.springframework.http.HttpMethod.GET;
import static org.springframework.http.HttpMethod.POST;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withServerError;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

class AutomatedBatchServiceTest {

    private static final String USER_BASE_URL = "http://user-service.test/api/users";
    private static final String TRANSACTION_BASE_URL = "http://transaction-service.test/api/transactions";
    private static final String PAYMENT_BASE_URL = "http://payment-service.test/api/payments";

    private RestTemplate restTemplate;
    private MockRestServiceServer server;
    private AutomatedBatchService service;

    @BeforeEach
    void setUp() {
        restTemplate = new RestTemplate();
        service = new AutomatedBatchService(restTemplate);
        server = MockRestServiceServer.bindTo(restTemplate).build();

        ReflectionTestUtils.setField(service, "userServiceUrl", USER_BASE_URL);
        ReflectionTestUtils.setField(service, "transactionServiceUrl", TRANSACTION_BASE_URL);
        ReflectionTestUtils.setField(service, "paymentServiceUrl", PAYMENT_BASE_URL);
    }

    @Test
    void runBatchEveryTwoMinutesExecutesExpectedWorkflow() {
        server.expect(requestTo(USER_BASE_URL + "/create"))
                .andExpect(method(POST))
                .andRespond(withSuccess("{\"accountNumber\":\"SRC-123\"}", MediaType.APPLICATION_JSON));
        server.expect(requestTo(USER_BASE_URL + "/create"))
                .andExpect(method(POST))
                .andRespond(withSuccess("{\"accountNumber\":\"DST-456\"}", MediaType.APPLICATION_JSON));
        server.expect(requestTo(USER_BASE_URL + "/login"))
                .andExpect(method(POST))
                .andRespond(withSuccess("Login successful", MediaType.TEXT_PLAIN));
        server.expect(requestTo(USER_BASE_URL + "/login"))
                .andExpect(method(POST))
                .andRespond(withSuccess("Login successful", MediaType.TEXT_PLAIN));
        server.expect(requestTo(USER_BASE_URL + "/SRC-123/balance"))
                .andExpect(method(GET))
                .andRespond(withSuccess("{\"balance\":2000}", MediaType.APPLICATION_JSON));
        server.expect(requestTo(USER_BASE_URL + "/DST-456/balance"))
                .andExpect(method(GET))
                .andRespond(withSuccess("{\"balance\":500}", MediaType.APPLICATION_JSON));
        server.expect(requestTo(TRANSACTION_BASE_URL + "/transfer"))
                .andExpect(method(POST))
                .andRespond(withSuccess("{\"status\":\"SUCCESS\"}", MediaType.APPLICATION_JSON));
        server.expect(requestTo(PAYMENT_BASE_URL + "/checkout"))
                .andExpect(method(POST))
                .andRespond(withSuccess("{\"status\":\"SUCCESS\"}", MediaType.APPLICATION_JSON));
        server.expect(requestTo(PAYMENT_BASE_URL + "/checkout"))
                .andExpect(method(POST))
                .andRespond(withStatus(HttpStatus.BAD_REQUEST));
        server.expect(requestTo(USER_BASE_URL + "/login"))
                .andExpect(method(POST))
                .andRespond(withStatus(HttpStatus.BAD_REQUEST));

        assertDoesNotThrow(() -> service.runBatchEveryTwoMinutes());

        server.verify();
    }

    @Test
    void runBatchEveryTwoMinutesSwallowsBatchExceptions() {
        server.expect(requestTo(USER_BASE_URL + "/create"))
                .andExpect(method(POST))
                .andRespond(withServerError());

        assertDoesNotThrow(() -> service.runBatchEveryTwoMinutes());

        server.verify();
    }
}
