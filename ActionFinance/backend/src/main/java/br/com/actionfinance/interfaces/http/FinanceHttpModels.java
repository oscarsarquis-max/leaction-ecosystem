package br.com.actionfinance.interfaces.http;

import br.com.actionfinance.application.finance.FinancialFilter;
import br.com.actionfinance.application.finance.TitleSummary;
import br.com.actionfinance.application.finance.TitleView;
import br.com.actionfinance.application.integration.ExternalLookupView;
import br.com.actionfinance.domain.TitleStatus;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

public final class FinanceHttpModels {

    private FinanceHttpModels() {}

    public record TitleWriteRequest(
            String description,
            UUID counterpartyId,
            String sourceReference,
            String amountMinor,
            String currency,
            LocalDate competenceDate,
            LocalDate dueDate,
            UUID categoryId,
            Long version,
            String reason) {}

    public record VersionRequest(long version, String reason) {}

    public record TitleResponse(
            UUID id,
            String reference,
            String direction,
            String status,
            String description,
            UUID counterpartyId,
            String counterpartyCode,
            String counterpartyName,
            boolean counterpartyActive,
            UUID categoryId,
            String categoryCode,
            String categoryName,
            boolean categoryActive,
            String amountMinor,
            String currency,
            LocalDate competenceDate,
            LocalDate dueDate,
            boolean overdue,
            String settledAmountMinor,
            String outstandingAmountMinor,
            String settlementStatus,
            String originKind,
            String sourceReference,
            long version,
            Instant createdAt,
            Instant updatedAt,
            Instant confirmedAt,
            Instant cancelledAt,
            String cancellationReason,
            boolean demoCompany,
            LocalDate businessDate) {

        public static TitleResponse from(TitleView view, LocalDate businessDate) {
            return new TitleResponse(
                    view.id(),
                    view.reference(),
                    view.direction().name(),
                    view.status().name(),
                    view.description(),
                    view.counterpartyId(),
                    view.counterpartyCode(),
                    view.counterpartyName(),
                    view.counterpartyActive(),
                    view.categoryId(),
                    view.categoryCode(),
                    view.categoryName(),
                    view.categoryActive(),
                    view.amountMinor() == null ? null : view.amountMinor().toPlainString(),
                    view.currency(),
                    view.competenceDate(),
                    view.dueDate(),
                    view.overdue(),
                    view.settledAmountMinor() == null ? "0" : view.settledAmountMinor().toPlainString(),
                    view.outstandingAmountMinor() == null ? "0" : view.outstandingAmountMinor().toPlainString(),
                    view.settlementStatus() == null ? "NOT_APPLICABLE" : view.settlementStatus().name(),
                    view.originKind().name(),
                    view.sourceReference(),
                    view.version(),
                    view.createdAt(),
                    view.updatedAt(),
                    view.confirmedAt(),
                    view.cancelledAt(),
                    view.cancellationReason(),
                    view.companyDemo(),
                    businessDate);
        }
    }

    public record TitleListResponse(
            List<TitleResponse> items,
            long totalItems,
            int page,
            int size,
            TitleSummaryResponse summary,
            LocalDate businessDate) {}

    public record TitleSummaryResponse(
            long openCount,
            String openAmountMinor,
            long overdueCount,
            String overdueAmountMinor,
            long draftCount) {
        public static TitleSummaryResponse from(TitleSummary summary) {
            return new TitleSummaryResponse(
                    summary.openCount(),
                    summary.openAmountMinor() == null ? "0" : summary.openAmountMinor().toPlainString(),
                    summary.overdueCount(),
                    summary.overdueAmountMinor() == null ? "0" : summary.overdueAmountMinor().toPlainString(),
                    summary.draftCount());
        }
    }

    public record HistoryResponse(
            List<HistoryItem> items) {}

    public record HistoryItem(
            UUID id,
            long titleVersion,
            String action,
            UUID actorId,
            String actorDisplayName,
            Instant occurredAt,
            String reason,
            String changesJson) {}

    public record CatalogWriteRequest(String name, String role, String direction, Long version, Boolean active) {}

    public record AccountWriteRequest(
            String name, String type, LocalDate openedOn, String openingBalanceMinor, Long version, Boolean active) {}

    public record AccountResponse(
            UUID id,
            String code,
            String name,
            String type,
            String currency,
            boolean active,
            LocalDate openedOn,
            String currentBalanceMinor,
            String companyName,
            long version) {
        public static AccountResponse from(br.com.actionfinance.application.finance.AccountView view) {
            return new AccountResponse(
                    view.id(),
                    view.code(),
                    view.name(),
                    view.type().name(),
                    view.currency(),
                    view.active(),
                    view.openedOn(),
                    view.currentBalanceMinor() == null ? "0" : view.currentBalanceMinor().toPlainString(),
                    view.companyName(),
                    view.version());
        }
    }

    public record MovementResponse(
            UUID id,
            String kind,
            LocalDate effectiveDate,
            Instant recordedAt,
            UUID recordedBy,
            String description,
            String inflowMinor,
            String outflowMinor,
            String balanceAfterMinor,
            UUID settlementId,
            UUID reversalId) {}

    public record MovementPageResponse(
            List<MovementResponse> items,
            long totalItems,
            int page,
            int size,
            String previousBalanceMinor,
            String periodEndBalanceMinor,
            String currentBalanceMinor,
            LocalDate from,
            LocalDate to) {}

    public record SettlementWriteRequest(
            UUID accountId,
            String amountMinor,
            LocalDate effectiveDate,
            String method,
            String note,
            Long version) {}

    public record ReversalWriteRequest(LocalDate effectiveDate, String reason, Long version) {}

    public record SettlementResponse(
            UUID id,
            UUID titleId,
            String titleReference,
            String titleDescription,
            String counterpartyName,
            String direction,
            UUID accountId,
            String accountName,
            boolean accountActive,
            String amountMinor,
            String currency,
            LocalDate effectiveDate,
            String method,
            String note,
            String originKind,
            Instant recordedAt,
            String actorDisplayName,
            boolean reversed,
            UUID reversalId,
            LocalDate reversalEffectiveDate,
            String reversalReason,
            Instant reversalRecordedAt,
            String reversalActorDisplayName,
            UUID movementId,
            UUID reversalMovementId,
            String titleSettledAmountMinor,
            String titleOutstandingAmountMinor,
            long titleVersion) {
        public static SettlementResponse from(br.com.actionfinance.application.finance.SettlementView view) {
            return new SettlementResponse(
                    view.id(),
                    view.titleId(),
                    view.titleReference(),
                    view.titleDescription(),
                    view.counterpartyName(),
                    view.direction().name(),
                    view.accountId(),
                    view.accountName(),
                    view.accountActive(),
                    view.amountMinor().toPlainString(),
                    view.currency(),
                    view.effectiveDate(),
                    view.method().name(),
                    view.note(),
                    view.originKind().name(),
                    view.recordedAt(),
                    view.actorDisplayName(),
                    view.reversed(),
                    view.reversalId(),
                    view.reversalEffectiveDate(),
                    view.reversalReason(),
                    view.reversalRecordedAt(),
                    view.reversalActorDisplayName(),
                    view.movementId(),
                    view.reversalMovementId(),
                    view.titleSettledAmountMinor() == null ? "0" : view.titleSettledAmountMinor().toPlainString(),
                    view.titleOutstandingAmountMinor() == null
                            ? "0"
                            : view.titleOutstandingAmountMinor().toPlainString(),
                    view.titleVersion());
        }
    }

    public static FinancialFilter parseFinancial(String raw, TitleStatus documentary) {
        if (documentary == TitleStatus.DRAFT || documentary == TitleStatus.CANCELLED) {
            return FinancialFilter.ALL;
        }
        if (raw == null || raw.isBlank() || "PENDING".equalsIgnoreCase(raw)) {
            return FinancialFilter.PENDING;
        }
        if ("ALL".equalsIgnoreCase(raw)) {
            return FinancialFilter.ALL;
        }
        try {
            return FinancialFilter.valueOf(raw.trim().toUpperCase());
        } catch (IllegalArgumentException ex) {
            throw new IllegalArgumentException("settlement");
        }
    }

    public record ExternalLookupResponse(
            UUID id,
            UUID companyId,
            UUID titleId,
            String originSystem,
            String externalReference,
            String amountMinor,
            String currency,
            String externalStatus,
            String deliveryStatus,
            String correlationId,
            String spiderDecisionId,
            String providerReference,
            String providerOrigin,
            String lastError,
            Instant observedAt,
            Instant updatedAt,
            Instant lastAttemptAt,
            String lastAttemptOutcome,
            UUID lastAttemptId,
            boolean automaticSettlement,
            boolean homolog) {
        public static ExternalLookupResponse from(ExternalLookupView view) {
            return new ExternalLookupResponse(
                    view.id(),
                    view.companyId(),
                    view.titleId(),
                    view.originSystem(),
                    view.externalReference(),
                    view.amountMinor() == null ? null : view.amountMinor().toPlainString(),
                    view.currency(),
                    view.externalStatus(),
                    view.deliveryStatus(),
                    view.correlationId(),
                    view.spiderDecisionId(),
                    view.providerReference(),
                    view.providerOrigin(),
                    view.lastError(),
                    view.observedAt(),
                    view.updatedAt(),
                    view.lastAttemptAt(),
                    view.lastAttemptOutcome(),
                    view.lastAttemptId(),
                    view.automaticSettlement(),
                    view.homolog());
        }
    }

    public record ExternalLookupRequest(String externalReference) {}

    public static TitleStatus parseStatus(String raw) {
        if (raw == null || raw.isBlank() || "OPEN".equalsIgnoreCase(raw)) {
            return TitleStatus.OPEN;
        }
        if ("ALL".equalsIgnoreCase(raw)) {
            return null;
        }
        try {
            return TitleStatus.valueOf(raw.trim().toUpperCase());
        } catch (IllegalArgumentException ex) {
            throw new IllegalArgumentException("status");
        }
    }
}
