package com.banking.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class TransactionRequest {
    private String sourceAccountNumber;
    private String destinationAccountNumber;
    private Double amount;
    private String description;
    private String username;
}