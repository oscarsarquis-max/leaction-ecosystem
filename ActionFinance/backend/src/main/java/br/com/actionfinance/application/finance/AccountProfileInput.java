package br.com.actionfinance.application.finance;

import java.util.List;

public record AccountProfileInput(
        String institutionName,
        String bankCode,
        String modality,
        String branchNumber,
        String branchDigit,
        String accountNumber,
        String accountDigit,
        String countryCode,
        String institutionEmail,
        String institutionPhone,
        List<AccountContactInput> contacts) {}
