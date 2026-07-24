package com.banking.userservice.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.banking.userservice.model.AccountStatus;
import com.banking.userservice.model.UserAccount;
import com.banking.userservice.repository.UserAccountRepository;
import java.math.BigDecimal;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

@ExtendWith(MockitoExtension.class)
class UserAccountControllerTest {

    private static final PasswordEncoder PASSWORD_ENCODER = new BCryptPasswordEncoder();

    @Mock
    private UserAccountRepository repository;

    @InjectMocks
    private UserAccountController controller;

    @Test
    void createAccountAssignsDefaultsAndPersistsAccount() {
        UserAccount request = new UserAccount();
        request.setUsername("alice");
        request.setPassword("secret");
        when(repository.save(any(UserAccount.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ResponseEntity<?> response = controller.createAccount(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        UserAccount savedAccount = (UserAccount) response.getBody();
        assertThat(savedAccount).isNotNull();
        assertThat(savedAccount.getAccountNumber()).startsWith("ACC");
        assertThat(savedAccount.getBalance()).isEqualByComparingTo(BigDecimal.ZERO);
        assertThat(savedAccount.getPassword()).isNotEqualTo("secret");
        assertThat(PASSWORD_ENCODER.matches("secret", savedAccount.getPassword())).isTrue();
        assertThat(savedAccount.getStatus()).isEqualTo(AccountStatus.ACTIVE);
        verify(repository).save(request);
    }

    @Test
    void getBalanceReturnsAccountSummary() {
        UserAccount account = new UserAccount();
        account.setAccountNumber("ACC123456");
        account.setBalance(new BigDecimal("150.50"));
        account.setStatus(AccountStatus.ACTIVE);
        when(repository.findByAccountNumber("ACC123456")).thenReturn(Optional.of(account));

        ResponseEntity<?> response = controller.getBalance("ACC123456");

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isEqualTo(Map.of(
                "accountNumber", "ACC123456",
                "balance", new BigDecimal("150.50"),
                "status", AccountStatus.ACTIVE
        ));
    }

    @Test
    void getBalanceThrowsWhenAccountDoesNotExist() {
        when(repository.findByAccountNumber("missing")).thenReturn(Optional.empty());

        RuntimeException exception =
                assertThrows(RuntimeException.class, () -> controller.getBalance("missing"));

        assertThat(exception).hasMessage("Account not found");
    }

    @Test
    void loginRejectsInvalidPassword() {
        UserAccount account = buildAccount("alice", "secret", AccountStatus.ACTIVE, "10.00");
        when(repository.findByUsername("alice")).thenReturn(Optional.of(account));

        ResponseEntity<?> response = controller.login(Map.of(
                "username", "alice",
                "password", "wrong"
        ));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody()).isEqualTo("Invalid password");
    }

    @Test
    void loginRejectsInactiveAccount() {
        UserAccount account = buildAccount("alice", "secret", AccountStatus.BLOCKED, "10.00");
        when(repository.findByUsername("alice")).thenReturn(Optional.of(account));

        ResponseEntity<?> response = controller.login(Map.of(
                "username", "alice",
                "password", "secret"
        ));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody()).isEqualTo("Account is not active");
    }

    @Test
    void loginSucceedsForActiveAccountWithMatchingPassword() {
        UserAccount account = buildAccount("alice", "secret", AccountStatus.ACTIVE, "10.00");
        when(repository.findByUsername("alice")).thenReturn(Optional.of(account));

        ResponseEntity<?> response = controller.login(Map.of(
                "username", "alice",
                "password", "secret"
        ));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isEqualTo("Login successful");
    }

    @Test
    void updateBalanceRejectsInactiveAccount() {
        UserAccount account = buildAccount("alice", "secret", AccountStatus.BLOCKED, "10.00");
        account.setAccountNumber("ACC123");
        when(repository.findByAccountNumber("ACC123")).thenReturn(Optional.of(account));

        ResponseEntity<?> response = controller.updateBalance(Map.of(
                "accountNumber", "ACC123",
                "amount", "5.00"
        ));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody()).isEqualTo("Account is not active");
        verify(repository, never()).save(any(UserAccount.class));
    }

    @Test
    void updateBalanceRejectsInsufficientFunds() {
        UserAccount account = buildAccount("alice", "secret", AccountStatus.ACTIVE, "10.00");
        account.setAccountNumber("ACC123");
        when(repository.findByAccountNumber("ACC123")).thenReturn(Optional.of(account));

        ResponseEntity<?> response = controller.updateBalance(Map.of(
                "accountNumber", "ACC123",
                "amount", "-20.00"
        ));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody()).isEqualTo("Insufficient balance");
        verify(repository, never()).save(any(UserAccount.class));
    }

    @Test
    void updateBalancePersistsNewBalanceForActiveAccount() {
        UserAccount account = buildAccount("alice", "secret", AccountStatus.ACTIVE, "10.00");
        account.setAccountNumber("ACC123");
        when(repository.findByAccountNumber("ACC123")).thenReturn(Optional.of(account));

        ResponseEntity<?> response = controller.updateBalance(Map.of(
                "accountNumber", "ACC123",
                "amount", "15.50"
        ));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isEqualTo("Balance updated successfully");

        ArgumentCaptor<UserAccount> captor = ArgumentCaptor.forClass(UserAccount.class);
        verify(repository).save(captor.capture());
        assertThat(captor.getValue().getBalance()).isEqualByComparingTo("25.50");
    }

    private UserAccount buildAccount(
            String username,
            String password,
            AccountStatus status,
            String balance
    ) {
        UserAccount account = new UserAccount();
        account.setUsername(username);
        account.setPassword(PASSWORD_ENCODER.encode(password));
        account.setStatus(status);
        account.setBalance(new BigDecimal(balance));
        return account;
    }
}
