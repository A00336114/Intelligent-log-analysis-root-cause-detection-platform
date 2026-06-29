package com.banking.paymentservice.controller;

import com.banking.paymentservice.dto.PaymentRequest;
import com.banking.paymentservice.model.Payment;
import com.banking.paymentservice.model.PaymentStatus;
import com.banking.paymentservice.repository.PaymentRepository;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.UUID;

@RestController
@RequestMapping("/api/payments")
public class PaymentController {

    private final PaymentRepository repository;

    public PaymentController(PaymentRepository repository) {
        this.repository = repository;
    }

    @PostMapping("/checkout")
    public ResponseEntity<?> checkout(@RequestBody PaymentRequest request) {

        String reference = "PAY" + UUID.randomUUID().toString()
                .substring(0, 10)
                .toUpperCase();

        if (request.getAmount() == null || request.getAmount().signum() <= 0) {
            return ResponseEntity.badRequest().body("Payment amount must be greater than zero");
        }

        if (request.getAmount().doubleValue() > 5000) {
            Payment blocked = new Payment();
            blocked.setPaymentReference(reference);
            blocked.setAccountNumber(request.getAccountNumber());
            blocked.setMerchantName(request.getMerchantName());
            blocked.setAmount(request.getAmount());
            blocked.setStatus(PaymentStatus.BLOCKED);
            blocked.setReason("High value payment blocked for risk review");
            blocked.setPaymentTime(LocalDateTime.now());

            repository.save(blocked);
            return ResponseEntity.badRequest().body(blocked);
        }

        Payment payment = new Payment();
        payment.setPaymentReference(reference);
        payment.setAccountNumber(request.getAccountNumber());
        payment.setMerchantName(request.getMerchantName());
        payment.setAmount(request.getAmount());
        payment.setStatus(PaymentStatus.SUCCESS);
        payment.setReason("Payment processed successfully");
        payment.setPaymentTime(LocalDateTime.now());

        repository.save(payment);
        return ResponseEntity.ok(payment);
    }

    @GetMapping
    public ResponseEntity<?> getPayments() {
        return ResponseEntity.ok(repository.findAll());
    }
}