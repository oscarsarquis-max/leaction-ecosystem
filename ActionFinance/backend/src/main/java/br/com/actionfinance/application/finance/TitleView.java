package br.com.actionfinance.application.finance;

import br.com.actionfinance.domain.HistoryAction;
import br.com.actionfinance.domain.OriginKind;
import br.com.actionfinance.domain.SettlementStatus;
import br.com.actionfinance.domain.TitleDirection;
import br.com.actionfinance.domain.TitleStatus;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

@JsonIgnoreProperties(ignoreUnknown = true)
public record TitleView(
        UUID id,
        UUID tenantId,
        UUID companyId,
        String reference,
        TitleDirection direction,
        TitleStatus status,
        String description,
        UUID counterpartyId,
        String counterpartyCode,
        String counterpartyName,
        boolean counterpartyActive,
        UUID categoryId,
        String categoryCode,
        String categoryName,
        boolean categoryActive,
        BigDecimal amountMinor,
        String currency,
        LocalDate competenceDate,
        LocalDate dueDate,
        boolean overdue,
        OriginKind originKind,
        String sourceReference,
        long version,
        Instant createdAt,
        Instant updatedAt,
        UUID createdBy,
        UUID updatedBy,
        Instant confirmedAt,
        Instant cancelledAt,
        String cancellationReason,
        boolean companyDemo,
        BigDecimal settledAmountMinor,
        BigDecimal outstandingAmountMinor,
        SettlementStatus settlementStatus) {

    public TitleView {
        if (settledAmountMinor == null) {
            settledAmountMinor = BigDecimal.ZERO;
        }
        if (outstandingAmountMinor == null) {
            outstandingAmountMinor = amountMinor == null ? BigDecimal.ZERO : amountMinor;
        }
        if (settlementStatus == null) {
            settlementStatus = SettlementStatus.derive(status, amountMinor, settledAmountMinor);
        }
    }

    public record HistoryEntry(
            UUID id,
            long titleVersion,
            HistoryAction action,
            UUID actorId,
            String actorDisplayName,
            Instant occurredAt,
            String reason,
            String changesJson) {}

    public record Page(
            List<TitleView> items,
            long totalItems,
            int page,
            int size,
            TitleSummary summary,
            LocalDate businessDate) {}
}
