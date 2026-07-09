package com.banking.loggenerator.service;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

@Service
public class AutomatedBatchService {

    private static final Logger log = LoggerFactory.getLogger(AutomatedBatchService.class);
    private static final String PASSWORD = "1234";

    private final RestTemplate restTemplate;

    @Autowired
    public AutomatedBatchService(RestTemplateBuilder restTemplateBuilder) {
        this(restTemplateBuilder.build());
    }

    AutomatedBatchService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    @Value("${services.user.base-url:http://user-service:8081/api/users}")
    private String userServiceUrl;

    @Value("${services.transaction.base-url:http://transaction-service:8082/api/transactions}")
    private String transactionServiceUrl;

    @Value("${services.payment.base-url:http://payment-service:8083/api/payments}")
    private String paymentServiceUrl;

    @Scheduled(
            initialDelayString = "${batch.schedule.initial-delay-ms:60000}",
            fixedRateString = "${batch.schedule.fixed-rate-ms:120000}"
    )
    public void runBatchEveryTwoMinutes() {
        String runId = UUID.randomUUID().toString().substring(0, 8);

        log.info("BATCH_STARTED runId={} time={}", runId, LocalDateTime.now());

        try {
            Map<String, Object> sourceUser = createUser("source", runId, 2000);
            Map<String, Object> destinationUser = createUser("destination", runId, 500);

            String sourceAccount = sourceUser.get("accountNumber").toString();
            String destinationAccount = destinationUser.get("accountNumber").toString();
            String sourceUsername = "source_user_" + runId;
            String destinationUsername = "destination_user_" + runId;

            login(sourceUsername);
            login(destinationUsername);

            checkBalance(sourceAccount);
            checkBalance(destinationAccount);

            transfer(sourceAccount, destinationAccount, new BigDecimal("100.00"), runId);
            payment(sourceAccount, "Amazon-" + runId, new BigDecimal("250.00"));
            highValuePayment(sourceAccount, "LuxuryStore-" + runId, new BigDecimal("10000.00"));
            invalidLogin(sourceUsername);

            log.info("BATCH_COMPLETED runId={}", runId);
        } catch (Exception exception) {
            log.error("BATCH_FAILED runId={}", runId, exception);
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> createUser(String type, String runId, int balance) {
        String username = type + "_user_" + runId;

        Map<String, Object> request = new LinkedHashMap<>();
        request.put("fullName", "Auto " + type + " User " + runId);
        request.put("username", username);
        request.put("password", PASSWORD);
        request.put("email", username + "@securebank.com");
        request.put("balance", balance);

        log.info("Creating user username={}", username);

        Map<String, Object> response = restTemplate.postForObject(
                userServiceUrl + "/create",
                request,
                Map.class
        );

        if (response == null || response.get("accountNumber") == null) {
            throw new IllegalStateException("User service did not return an account number for " + username);
        }

        log.info("User created username={} accountNumber={}", username, response.get("accountNumber"));
        return response;
    }

    private void login(String username) {
        Map<String, String> request = Map.of(
                "username", username,
                "password", PASSWORD
        );

        log.info("Login started username={}", username);
        restTemplate.postForObject(userServiceUrl + "/login", request, String.class);
        log.info("Login successful username={}", username);
    }

    private void invalidLogin(String username) {
        try {
            Map<String, String> request = Map.of(
                    "username", username,
                    "password", "wrong-password"
            );

            log.warn("Invalid login simulation username={}", username);
            restTemplate.postForObject(userServiceUrl + "/login", request, String.class);
        } catch (Exception exception) {
            log.warn("Invalid login failed as expected username={}", username);
        }
    }

    private void checkBalance(String accountNumber) {
        log.info("Checking balance accountNumber={}", accountNumber);

        Object response = restTemplate.getForObject(
                userServiceUrl + "/" + accountNumber + "/balance",
                Object.class
        );

        log.info("Balance checked accountNumber={} response={}", accountNumber, response);
    }

    private void transfer(String sourceAccount, String destinationAccount, BigDecimal amount, String runId) {
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("sourceAccountNumber", sourceAccount);
        request.put("destinationAccountNumber", destinationAccount);
        request.put("amount", amount);
        request.put("description", "Automated batch transfer runId=" + runId);

        log.info("Transfer started source={} destination={} amount={}", sourceAccount, destinationAccount, amount);

        Object response = restTemplate.postForObject(
                transactionServiceUrl + "/transfer",
                request,
                Object.class
        );

        log.info("Transfer completed response={}", response);
    }

    private void payment(String accountNumber, String merchant, BigDecimal amount) {
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("accountNumber", accountNumber);
        request.put("merchantName", merchant);
        request.put("amount", amount);

        log.info("Payment started account={} merchant={} amount={}", accountNumber, merchant, amount);

        Object response = restTemplate.postForObject(
                paymentServiceUrl + "/checkout",
                request,
                Object.class
        );

        log.info("Payment completed response={}", response);
    }

    private void highValuePayment(String accountNumber, String merchant, BigDecimal amount) {
        try {
            Map<String, Object> request = new LinkedHashMap<>();
            request.put("accountNumber", accountNumber);
            request.put("merchantName", merchant);
            request.put("amount", amount);

            log.warn("High value payment started account={} amount={}", accountNumber, amount);
            restTemplate.postForObject(paymentServiceUrl + "/checkout", request, Object.class);
        } catch (Exception exception) {
            log.warn("High value payment blocked as expected account={}", accountNumber);
        }
    }
}
