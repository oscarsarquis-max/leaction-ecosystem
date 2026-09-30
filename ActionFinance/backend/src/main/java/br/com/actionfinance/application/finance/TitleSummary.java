package br.com.actionfinance.application.finance;

import java.math.BigDecimal;

public record TitleSummary(
        long openCount,
        BigDecimal openAmountMinor,
        long overdueCount,
        BigDecimal overdueAmountMinor,
        long draftCount) {}
