package com.banking.transaction.repository;

import com.banking.transaction.model.AccountLedger;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface AccountLedgerRepository extends JpaRepository<AccountLedger, Long> {

    Optional<AccountLedger> findByTransactionReference(String transactionReference);

    List<AccountLedger> findBySourceAccountNumber(String sourceAccountNumber);

    List<AccountLedger> findByDestinationAccountNumber(String destinationAccountNumber);
}