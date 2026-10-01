package br.com.actionfinance.application.integration;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public final class PayReceiptViews {

    private PayReceiptViews() {}

    public record TransactionView(
            UUID id,
            UUID companyId,
            String environment,
            String transactionId,
            String orderReference,
            String processorReference,
            String originalStatus,
            String normalizedStatus,
            String amountMinor,
            String currency,
            boolean amountAbsent,
            boolean reviewRequired,
            boolean testLabeled,
            Instant originCreatedAt,
            Instant originUpdatedAt,
            Instant originRevision,
            UUID lastSyncRunId,
            String lastCorrelationId,
            Instant updatedAt) {}

    public record RevisionView(
            UUID id,
            Instant observedAt,
            String originalStatus,
            String normalizedStatus,
            String amountMinor,
            String currency,
            boolean reviewRequired,
            Instant originRevision,
            String correlationId) {}

    public record SyncRunView(
            UUID id,
            String environment,
            String status,
            String rootCorrelationId,
            String spiderMessageId,
            String resumeCursor,
            int pageCount,
            int importedCount,
            int updatedCount,
            int reviewCount,
            String lastError,
            Instant startedAt,
            Instant finishedAt,
            String monitorUrl) {}

    public record SyncPageView(
            int pageNo,
            String correlationId,
            String spiderMessageId,
            int itemCount,
            String outcome) {}

    public record SyncResult(
            SyncRunView run,
            List<TransactionView> items,
            boolean resumed,
            boolean concurrentRejected) {}
}
