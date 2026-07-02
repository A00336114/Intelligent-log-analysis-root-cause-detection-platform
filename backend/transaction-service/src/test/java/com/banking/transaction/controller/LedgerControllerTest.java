package com.banking.transaction.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.banking.transaction.dto.TransferRequest;
import com.banking.transaction.model.AccountLedger;
import com.banking.transaction.model.TransactionStatus;
import com.banking.transaction.repository.AccountLedgerRepository;
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
import org.springframework.web.client.RestTemplate;

@ExtendWith(MockitoExtension.class)
class LedgerControllerTest {

    private static final String USER_SERVICE_URL =
            "http://user-service:8081/api/users/internal/update-balance";

    @Mock
    private AccountLedgerRepository repository;

    @Mock
    private RestTemplate restTemplate;

    @InjectMocks
    private LedgerController controller;

    @Test
    void transferRejectsNonPositiveAmount() {
        TransferRequest request = request("SRC-1", "DST-1", "0.00");

        ResponseEntity<?> response = controller.transfer(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody()).isEqualTo("Amount must be greater than zero");
        verify(repository, never()).save(any(AccountLedger.class));
    }

    @Test
    void transferRejectsMissingAccountNumbers() {
        TransferRequest request = new TransferRequest();
        request.setAmount(new BigDecimal("10.00"));

        ResponseEntity<?> response = controller.transfer(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody()).isEqualTo("Source and destination account numbers are required");
        verify(repository, never()).save(any(AccountLedger.class));
    }

    @Test
    void transferRejectsSameSourceAndDestinationAccount() {
        TransferRequest request = request("ACC-1", "ACC-1", "10.00");

        ResponseEntity<?> response = controller.transfer(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody()).isEqualTo("Source and destination account cannot be same");
        verify(repository, never()).save(any(AccountLedger.class));
    }

    @Test
    void transferPersistsSuccessfulLedgerWhenBalanceUpdatesSucceed() {
        TransferRequest request = request("SRC-1", "DST-1", "25.00");
        request.setDescription("Monthly transfer");
        when(restTemplate.postForEntity(eq(USER_SERVICE_URL), anyMap(), eq(String.class)))
                .thenReturn(ResponseEntity.ok("ok"), ResponseEntity.ok("ok"));
        when(repository.save(any(AccountLedger.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ResponseEntity<?> response = controller.transfer(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        AccountLedger ledger = (AccountLedger) response.getBody();
        assertThat(ledger).isNotNull();
        assertThat(ledger.getTransactionReference()).startsWith("TXN");
        assertThat(ledger.getStatus()).isEqualTo(TransactionStatus.SUCCESS);
        assertThat(ledger.getDescription()).isEqualTo("Monthly transfer");

        ArgumentCaptor<AccountLedger> captor = ArgumentCaptor.forClass(AccountLedger.class);
        verify(repository).save(captor.capture());
        assertThat(captor.getValue().getStatus()).isEqualTo(TransactionStatus.SUCCESS);
        assertThat(captor.getValue().getAmount()).isEqualByComparingTo("25.00");
        verify(restTemplate, times(2)).postForEntity(eq(USER_SERVICE_URL), anyMap(), eq(String.class));
    }

    @Test
    void transferPersistsFailedLedgerWhenUserServiceCallThrows() {
        TransferRequest request = request("SRC-1", "DST-1", "25.00");
        when(restTemplate.postForEntity(eq(USER_SERVICE_URL), anyMap(), eq(String.class)))
                .thenThrow(new RuntimeException("service unavailable"));
        when(repository.save(any(AccountLedger.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ResponseEntity<?> response = controller.transfer(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        AccountLedger ledger = (AccountLedger) response.getBody();
        assertThat(ledger).isNotNull();
        assertThat(ledger.getStatus()).isEqualTo(TransactionStatus.FAILED);
        assertThat(ledger.getDescription()).contains("Transfer failed: service unavailable");

        ArgumentCaptor<AccountLedger> captor = ArgumentCaptor.forClass(AccountLedger.class);
        verify(repository).save(captor.capture());
        assertThat(captor.getValue().getStatus()).isEqualTo(TransactionStatus.FAILED);
    }

    @Test
    void getAllTransactionsReturnsRepositoryResults() {
        AccountLedger ledger = new AccountLedger();
        ledger.setTransactionReference("TXN123");
        when(repository.findAll()).thenReturn(List.of(ledger));

        ResponseEntity<?> response = controller.getAllTransactions();

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isEqualTo(List.of(ledger));
    }

    private TransferRequest request(String source, String destination, String amount) {
        TransferRequest request = new TransferRequest();
        request.setSourceAccountNumber(source);
        request.setDestinationAccountNumber(destination);
        request.setAmount(new BigDecimal(amount));
        return request;
    }
}
