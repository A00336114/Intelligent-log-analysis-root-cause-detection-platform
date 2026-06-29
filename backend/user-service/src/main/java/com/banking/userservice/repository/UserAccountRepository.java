package com.banking.userservice.repository;

import com.banking.userservice.model.UserAccount;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface UserAccountRepository extends JpaRepository<UserAccount, Long> {
    Optional<UserAccount> findByAccountNumber(String accountNumber);
    Optional<UserAccount> findByUsername(String username);
}