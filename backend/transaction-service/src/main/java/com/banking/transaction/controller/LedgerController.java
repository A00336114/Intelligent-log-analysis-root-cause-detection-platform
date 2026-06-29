package com.banking.transaction.controller;

import com.banking.transaction.dto.TransferRequest;
import com.banking.transaction.model.AccountLedger;
import com.banking.transaction.model.TransactionStatus;
import com.banking.transaction.repository.AccountLedgerRepository;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/transactions")
public class LedgerController {

    private final AccountLedgerRepository repository;
    private final RestTemplate restTemplate;

    private static final String USER_SERVICE_URL =
            "http://user-service:8081/api/users/internal/update-balance";

    public LedgerController(AccountLedgerRepository repository, RestTemplate restTemplate) {
        this.repository = repository;
        this.restTemplate = restTemplate;
    }

    @PostMapping("/transfer")
    public ResponseEntity<?> transfer(@RequestBody TransferRequest request) {

        String reference = "TXN" + UUID.randomUUID().toString()
                .substring(0, 10)
                .toUpperCase();

        if (request.getAmount() == null || request.getAmount().signum() <= 0) {
            return ResponseEntity.badRequest().body("Amount must be greater than zero");
        }

        if (request.getSourceAccountNumber() == null ||
                request.getDestinationAccountNumber() == null) {
            return ResponseEntity.badRequest().body("Source and destination account numbers are required");
        }

        if (request.getSourceAccountNumber().equals(request.getDestinationAccountNumber())) {
            return ResponseEntity.badRequest().body("Source and destination account cannot be same");
        }

        try {
            restTemplate.postForEntity(
                    USER_SERVICE_URL,
                    Map.of(
                            "accountNumber", request.getSourceAccountNumber(),
                            "amount", request.getAmount().negate().toString()
                    ),
                    String.class
            );

            restTemplate.postForEntity(
                    USER_SERVICE_URL,
                    Map.of(
                            "accountNumber", request.getDestinationAccountNumber(),
                            "amount", request.getAmount().toString()
                    ),
                    String.class
            );

            AccountLedger ledger = new AccountLedger();
            ledger.setTransactionReference(reference);
            ledger.setSourceAccountNumber(request.getSourceAccountNumber());
            ledger.setDestinationAccountNumber(request.getDestinationAccountNumber());
            ledger.setAmount(request.getAmount());
            ledger.setStatus(TransactionStatus.SUCCESS);
            ledger.setDescription(request.getDescription());
            ledger.setTransactionTime(LocalDateTime.now());

            repository.save(ledger);

            return ResponseEntity.ok(ledger);

        } catch (Exception e) {

            AccountLedger failed = new AccountLedger();
            failed.setTransactionReference(reference);
            failed.setSourceAccountNumber(request.getSourceAccountNumber());
            failed.setDestinationAccountNumber(request.getDestinationAccountNumber());
            failed.setAmount(request.getAmount());
            failed.setStatus(TransactionStatus.FAILED);
            failed.setDescription("Transfer failed: " + e.getMessage());
            failed.setTransactionTime(LocalDateTime.now());

            repository.save(failed);

            return ResponseEntity.badRequest().body(failed);
        }
    }

    @GetMapping
    public ResponseEntity<?> getAllTransactions() {
        return ResponseEntity.ok(repository.findAll());
    }
}