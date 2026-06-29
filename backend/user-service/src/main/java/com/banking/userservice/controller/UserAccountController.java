package com.banking.userservice.controller;

import com.banking.userservice.model.AccountStatus;
import com.banking.userservice.model.UserAccount;
import com.banking.userservice.repository.UserAccountRepository;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/users")
public class UserAccountController {

    private final UserAccountRepository repository;

    public UserAccountController(UserAccountRepository repository) {
        this.repository = repository;
    }

    @PostMapping("/create")
    public ResponseEntity<?> createAccount(@RequestBody UserAccount account) {

        account.setAccountNumber("ACC" + UUID.randomUUID().toString()
                .substring(0, 8)
                .toUpperCase());

        if (account.getBalance() == null) {
            account.setBalance(BigDecimal.ZERO);
        }

        account.setStatus(AccountStatus.ACTIVE);

        return ResponseEntity.ok(repository.save(account));
    }

    @GetMapping("/{accountNumber}/balance")
    public ResponseEntity<?> getBalance(@PathVariable String accountNumber) {

        UserAccount account = repository.findByAccountNumber(accountNumber)
                .orElseThrow(() -> new RuntimeException("Account not found"));

        return ResponseEntity.ok(Map.of(
                "accountNumber", account.getAccountNumber(),
                "balance", account.getBalance(),
                "status", account.getStatus()
        ));
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody Map<String, String> request) {

        UserAccount account = repository.findByUsername(request.get("username"))
                .orElseThrow(() -> new RuntimeException("Invalid username"));

        if (!account.getPassword().equals(request.get("password"))) {
            return ResponseEntity.badRequest().body("Invalid password");
        }

        if (account.getStatus() != AccountStatus.ACTIVE) {
            return ResponseEntity.badRequest().body("Account is not active");
        }

        return ResponseEntity.ok("Login successful");
    }

    @PostMapping("/internal/update-balance")
    public ResponseEntity<?> updateBalance(@RequestBody Map<String, String> request) {

        String accountNumber = request.get("accountNumber");
        BigDecimal amount = new BigDecimal(request.get("amount"));

        UserAccount account = repository.findByAccountNumber(accountNumber)
                .orElseThrow(() -> new RuntimeException("Account not found"));

        if (account.getStatus() != AccountStatus.ACTIVE) {
            return ResponseEntity.badRequest().body("Account is not active");
        }

        BigDecimal newBalance = account.getBalance().add(amount);

        if (newBalance.compareTo(BigDecimal.ZERO) < 0) {
            return ResponseEntity.badRequest().body("Insufficient balance");
        }

        account.setBalance(newBalance);
        repository.save(account);

        return ResponseEntity.ok("Balance updated successfully");
    }
}