package com.banking.paymentservice.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.banking.paymentservice.dto.PaymentRequest;
import com.banking.paymentservice.model.Payment;
import com.banking.paymentservice.model.PaymentStatus;
import com.banking.paymentservice.repository.PaymentRepository;
import java.math.BigDecimal;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

@ExtendWith(MockitoExtension.class)
class PaymentControllerTest {

    @Mock
    private PaymentRepository repository;

    @InjectMocks
    private PaymentController controller;

    @Test
    void checkoutRejectsNonPositiveAmounts() {
        PaymentRequest request = paymentRequest("ACC-1", "Merchant", "0.00");

        ResponseEntity<?> response = controller.checkout(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody()).isEqualTo("Payment amount must be greater than zero");
        verify(repository, never()).save(any(Payment.class));
    }

    @Test
    void checkoutBlocksHighValuePayments() {
        PaymentRequest request = paymentRequest("ACC-1", "Luxury Shop", "6000.00");
        when(repository.save(any(Payment.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ResponseEntity<?> response = controller.checkout(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        Payment payment = (Payment) response.getBody();
        assertThat(payment).isNotNull();
        assertThat(payment.getStatus()).isEqualTo(PaymentStatus.BLOCKED);
        assertThat(payment.getReason()).isEqualTo("High value payment blocked for risk review");

        ArgumentCaptor<Payment> captor = ArgumentCaptor.forClass(Payment.class);
        verify(repository).save(captor.capture());
        assertThat(captor.getValue().getPaymentReference()).startsWith("PAY");
        assertThat(captor.getValue().getStatus()).isEqualTo(PaymentStatus.BLOCKED);
    }

    @Test
    void checkoutPersistsSuccessfulPayments() {
        PaymentRequest request = paymentRequest("ACC-1", "Coffee Shop", "49.99");
        when(repository.save(any(Payment.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ResponseEntity<?> response = controller.checkout(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        Payment payment = (Payment) response.getBody();
        assertThat(payment).isNotNull();
        assertThat(payment.getPaymentReference()).startsWith("PAY");
        assertThat(payment.getStatus()).isEqualTo(PaymentStatus.SUCCESS);
        assertThat(payment.getReason()).isEqualTo("Payment processed successfully");

        ArgumentCaptor<Payment> captor = ArgumentCaptor.forClass(Payment.class);
        verify(repository).save(captor.capture());
        assertThat(captor.getValue().getAmount()).isEqualByComparingTo("49.99");
    }

    @Test
    void getPaymentsReturnsRepositoryResults() {
        Payment payment = new Payment();
        payment.setPaymentReference("PAY123");
        when(repository.findAll()).thenReturn(List.of(payment));

        ResponseEntity<?> response = controller.getPayments();

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isEqualTo(List.of(payment));
    }

    private PaymentRequest paymentRequest(String accountNumber, String merchantName, String amount) {
        PaymentRequest request = new PaymentRequest();
        request.setAccountNumber(accountNumber);
        request.setMerchantName(merchantName);
        request.setAmount(new BigDecimal(amount));
        return request;
    }
}
