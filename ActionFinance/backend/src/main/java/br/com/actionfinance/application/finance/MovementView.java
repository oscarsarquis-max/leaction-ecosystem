package br.com.actionfinance.application.finance;

import br.com.actionfinance.domain.MovementKind;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

public record MovementView(
        UUID id,
        MovementKind kind,
        LocalDate effectiveDate,
        Instant recordedAt,
        UUID recordedBy,
        String description,
        BigDecimal inflowMinor,
        BigDecimal outflowMinor,
        BigDecimal balanceAfterMinor,
        UUID settlementId,
        UUID reversalId) {

    public record Page(
            List<MovementView> items,
            long totalItems,
            int page,
            int size,
            BigDecimal previousBalanceMinor,
            BigDecimal periodEndBalanceMinor,
            BigDecimal currentBalanceMinor,
            LocalDate from,
            LocalDate to) {}
}
