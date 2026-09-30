package br.com.actionfinance.application.finance;

import br.com.actionfinance.domain.OriginKind;
import br.com.actionfinance.domain.SettlementMethod;
import br.com.actionfinance.domain.TitleDirection;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

public record SettlementView(
        UUID id,
        UUID tenantId,
        UUID companyId,
        UUID titleId,
        String titleReference,
        String titleDescription,
        String counterpartyName,
        TitleDirection direction,
        UUID accountId,
        String accountName,
        boolean accountActive,
        BigDecimal amountMinor,
        String currency,
        LocalDate effectiveDate,
        SettlementMethod method,
        String note,
        OriginKind originKind,
        Instant recordedAt,
        UUID recordedBy,
        String actorDisplayName,
        boolean reversed,
        UUID reversalId,
        LocalDate reversalEffectiveDate,
        String reversalReason,
        Instant reversalRecordedAt,
        String reversalActorDisplayName,
        UUID movementId,
        UUID reversalMovementId,
        BigDecimal titleSettledAmountMinor,
        BigDecimal titleOutstandingAmountMinor,
        long titleVersion) {}
