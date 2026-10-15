package br.com.actionfinance.application.integration;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.finance.AuthorizedScope;
import br.com.actionfinance.application.finance.CompanyAccessService;
import br.com.actionfinance.application.finance.FinanceExceptions.ValidationException;
import br.com.actionfinance.application.finance.FinanceExceptions.VersionConflictException;
import br.com.actionfinance.application.identity.FinancePermissions;
import br.com.actionfinance.application.integration.PayReceiptViews.RevisionView;
import br.com.actionfinance.application.integration.PayReceiptViews.SyncResult;
import br.com.actionfinance.application.integration.PayReceiptViews.SyncRunView;
import br.com.actionfinance.application.integration.PayReceiptViews.TransactionView;
import br.com.actionfinance.application.integration.SpiderInteractionClient.SpiderListResult;
import br.com.actionfinance.configuration.ActionFinanceProperties;
import br.com.actionfinance.infrastructure.persistence.JdbcPayReceiptRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Service
public class PayReceiptSyncService {

    private final ActionFinanceProperties properties;
    private final CompanyAccessService companies;
    private final JdbcPayReceiptRepository receipts;
    private final SpiderInteractionClient spider;
    private final TransactionTemplate shortTx;

    public PayReceiptSyncService(
            ActionFinanceProperties properties,
            CompanyAccessService companies,
            JdbcPayReceiptRepository receipts,
            SpiderInteractionClient spider,
            PlatformTransactionManager transactions) {
        this.properties = properties;
        this.companies = companies;
        this.receipts = receipts;
        this.spider = spider;
        this.shortTx = new TransactionTemplate(transactions);
        this.shortTx.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
    }

    public Map<String, Object> overview(ApplicationPrincipal principal, UUID companyId, String requestedEnvironment) {
        companies.requirePermission(principal, companyId, FinancePermissions.TITLES_READ);
        AuthorizedScope scope = companies.requireActiveMembership(principal, companyId);
        String environment = resolveEnvironment(scope, requestedEnvironment);
        SyncRunView latest = receipts.latestRun(scope, environment).map(this::withMonitor).orElse(null);
        SyncRunView lastSuccessful =
                receipts.latestSuccessfulRun(scope, environment).map(this::withMonitor).orElse(null);
        List<TransactionView> items = receipts.list(scope, environment, 200);
        List<TransactionView> reviews = receipts.listReviews(scope, environment, 200);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("environment", environment);
        body.put("homolog", properties.getIntegration().isHomolog());
        body.put("receiptSyncEnabled", properties.getIntegration().isReceiptSyncEnabled());
        body.put("receiptSyncSuspended", !properties.getIntegration().isReceiptSyncAllowed());
        body.put("createsFinancialMovement", false);
        body.put("latestRun", latest);
        body.put("lastSuccessfulRun", lastSuccessful);
        body.put("storedCount", items.size() + reviews.size());
        body.put("items", items);
        body.put("reviews", reviews);
        body.put("operationalTotalsExcluded", true);
        return body;
    }

    public Map<String, Object> detail(ApplicationPrincipal principal, UUID companyId, UUID id) {
        companies.requirePermission(principal, companyId, FinancePermissions.TITLES_READ);
        AuthorizedScope scope = companies.requireActiveMembership(principal, companyId);
        TransactionView item =
                receipts.findById(scope, id).orElseThrow(() -> ValidationException.of("id", "Recebimento importado não encontrado."));
        List<RevisionView> history = receipts.revisions(scope, item.id());
        SyncRunView run = receipts.findRun(scope, item.lastSyncRunId()).map(this::withMonitor).orElse(null);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("item", item);
        body.put("history", history);
        body.put("run", run);
        body.put("createsFinancialMovement", false);
        return body;
    }

    public SyncResult synchronize(ApplicationPrincipal principal, UUID companyId, String requestedEnvironment) {
        if (!properties.getIntegration().isReceiptSyncAllowed()) {
            throw ValidationException.of(
                    "sync", "Sincronismo temporariamente suspenso durante a migração da Spider.");
        }
        requireReceiptSync();
        AuthorizedScope scope = companies.requireWritable(principal, companyId, FinancePermissions.TITLES_WRITE);
        String environment = resolveEnvironment(scope, requestedEnvironment);
        Instant now = Instant.now();
        UUID runId = UUID.randomUUID();
        String rootCorrelation = "afr-" + runId;
        java.time.Duration staleAfter = properties.getIntegration().getSyncStaleAfter();
        Instant staleThreshold =
                staleAfter == null || staleAfter.isNegative() ? now.minusSeconds(60) : now.minus(staleAfter);
        String startCursor =
                shortTx.execute(
                        status -> {
                            receipts.reclaimStaleRunning(scope, environment, staleThreshold, now);
                            if (receipts.findRunning(scope, environment).isPresent()) {
                                throw new VersionConflictException(
                                        "Já existe uma sincronização em andamento para esta empresa e ambiente.");
                            }
                            Optional<SyncRunView> latest = receipts.latestRun(scope, environment);
                            String cursor = null;
                            if (latest.isPresent()
                                    && ("PARTIAL".equals(latest.get().status()) || "FAILED".equals(latest.get().status()))
                                    && latest.get().resumeCursor() != null
                                    && !latest.get().resumeCursor().isBlank()) {
                                cursor = latest.get().resumeCursor();
                            }
                            if (!receipts.insertRunning(scope, runId, environment, rootCorrelation, cursor, now)) {
                                throw new VersionConflictException(
                                        "Já existe uma sincronização em andamento para esta empresa e ambiente.");
                            }
                            return cursor;
                        });
        boolean resumed = startCursor != null && !startCursor.isBlank();
        String cursor = startCursor;
        int pageNo = 0;
        Instant lastOrigin = null;
        String lastTxn = null;
        String lastCursor = startCursor;
        String lastMessageId = null;
        String previousFirstId = null;
        try {
            while (true) {
                pageNo++;
                if (pageNo > 20) {
                    Instant failedAt = Instant.now();
                    shortTx.executeWithoutResult(
                            status ->
                                    receipts.finishRun(
                                            scope,
                                            runId,
                                            "PARTIAL",
                                            "A janela de listagem não avançou e foi interrompida.",
                                            failedAt));
                    return resultOf(scope, environment, runId, resumed);
                }
                String pageCorrelation = "afp-" + runId + "-" + pageNo;
                int limit = Math.min(50, Math.max(1, properties.getIntegration().getSyncPageLimit()));
                SpiderListResult page =
                        spider.list(
                                pageCorrelation,
                                "list-" + runId + "-" + pageNo,
                                companyId.toString(),
                                environment,
                                cursor,
                                limit);
                if (page == null || !page.available()) {
                    String error =
                            page == null || page.errorMessage() == null
                                    ? "A Spider não devolveu a listagem."
                                    : page.errorMessage();
                    Instant failedAt = Instant.now();
                    String failStatus = pageNo == 1 ? "FAILED" : "PARTIAL";
                    shortTx.executeWithoutResult(status -> receipts.finishRun(scope, runId, failStatus, error, failedAt));
                    return resultOf(scope, environment, runId, resumed);
                }
                lastMessageId = page.messageId();
                String firstId = firstTransactionId(page);
                if (pageNo > 1 && firstId != null && firstId.equals(previousFirstId)) {
                    Instant failedAt = Instant.now();
                    shortTx.executeWithoutResult(
                            status ->
                                    receipts.finishRun(
                                            scope,
                                            runId,
                                            "PARTIAL",
                                            "A listagem repetiu a mesma página e foi interrompida.",
                                            failedAt));
                    return resultOf(scope, environment, runId, resumed);
                }
                previousFirstId = firstId;
                ApplyCounts counts = applyPage(scope, environment, runId, page, pageNo, cursor, Instant.now());
                lastCursor = page.nextCursor();
                if (counts.lastOriginUpdatedAt() != null) {
                    lastOrigin = counts.lastOriginUpdatedAt();
                    lastTxn = counts.lastTransactionId();
                }
                if (page.nextCursor() == null || page.nextCursor().isBlank()) {
                    break;
                }
                cursor = page.nextCursor();
            }
            Instant done = Instant.now();
            String finalCursor = lastCursor;
            Instant finalOrigin = lastOrigin;
            String finalTxn = lastTxn;
            String messageId = lastMessageId;
            shortTx.executeWithoutResult(
                    status -> {
                        receipts.attachMessage(scope, runId, messageId, done);
                        SyncRunView current = receipts.findRun(scope, runId).orElseThrow();
                        String endStatus =
                                current.importedCount() == 0 && current.updatedCount() == 0 ? "EMPTY" : "SUCCESS";
                        receipts.finishRun(scope, runId, endStatus, null, done);
                        receipts.advanceCheckpoint(scope, environment, finalCursor, finalOrigin, finalTxn, runId, done);
                    });
            return resultOf(scope, environment, runId, resumed);
        } catch (RuntimeException exception) {
            Instant failedAt = Instant.now();
            String failStatus = pageNo <= 1 ? "FAILED" : "PARTIAL";
            String failMessage = clip(exception.getMessage());
            shortTx.executeWithoutResult(status -> receipts.finishRun(scope, runId, failStatus, failMessage, failedAt));
            throw exception;
        }
    }

    public Map<String, Long> financialCounts(ApplicationPrincipal principal, UUID companyId) {
        requireReceiptSync();
        companies.requirePermission(principal, companyId, FinancePermissions.TITLES_READ);
        AuthorizedScope scope = companies.requireActiveMembership(principal, companyId);
        return Map.of(
                "titles", receipts.countTitles(scope),
                "settlements", receipts.countSettlements(scope),
                "cashMovements", receipts.countMovements(scope));
    }

    private ApplyCounts applyPage(
            AuthorizedScope scope,
            String environment,
            UUID runId,
            SpiderListResult page,
            int pageNo,
            String cursorSent,
            Instant now) {
        return shortTx.execute(
                status -> {
                    int imported = 0;
                    int updated = 0;
                    int review = 0;
                    Instant lastOrigin = null;
                    String lastTxn = null;
                    List<Map<String, Object>> incomingRows = new ArrayList<>();
                    if (page.items() != null) {
                        incomingRows.addAll(page.items());
                    }
                    if (page.reviews() != null) {
                        incomingRows.addAll(page.reviews());
                    }
                    for (Map<String, Object> raw : incomingRows) {
                        TransactionView incoming = toView(scope, environment, runId, page.correlationId(), raw, now);
                        if (incoming == null) {
                            review++;
                            continue;
                        }
                        Optional<TransactionView> stored =
                                receipts.findByIdentity(scope, environment, incoming.transactionId());
                        if (stored.isEmpty()) {
                            receipts.insertTransaction(scope, incoming);
                            imported++;
                        } else if (shouldApply(stored.get(), incoming)) {
                            receipts.updateTransaction(scope, merge(stored.get(), incoming));
                            updated++;
                        }
                        if (incoming.reviewRequired()) {
                            review++;
                        }
                        if (incoming.originRevision() != null
                                && (lastOrigin == null || !incoming.originRevision().isBefore(lastOrigin))) {
                            lastOrigin = incoming.originRevision();
                            lastTxn = incoming.transactionId();
                        }
                    }
                    receipts.markPageApplied(
                            scope,
                            runId,
                            pageNo,
                            cursorSent,
                            page.nextCursor(),
                            page.items() == null ? 0 : page.items().size(),
                            page.correlationId(),
                            page.messageId(),
                            imported,
                            updated,
                            review,
                            now);
                    return new ApplyCounts(imported, updated, review, lastOrigin, lastTxn);
                });
    }

    private TransactionView toView(
            AuthorizedScope scope,
            String environment,
            UUID runId,
            String correlationId,
            Map<String, Object> raw,
            Instant now) {
        if (raw == null) {
            return null;
        }
        String transactionId = text(raw.get("transactionId"));
        if (transactionId == null || transactionId.isBlank()) {
            return null;
        }
        String amount = amountMinor(raw.get("amountMinor"));
        boolean absent = amount == null || Boolean.TRUE.equals(raw.get("amountAbsent"));
        if (absent) {
            amount = null;
        }
        Instant created = parseInstant(raw.get("createdAt"));
        Instant updated = parseInstant(raw.get("updatedAt"));
        Instant revision = parseInstant(raw.get("originRevision"));
        if (revision == null) {
            revision = updated;
        }
        String currency = currency(raw.get("currency"));
        String paid = amountMinor(raw.get("paidAmountMinor"));
        boolean paidAbsent = paid == null;
        String normalized = normalizeStatus(text(raw.get("normalizedStatus")), text(raw.get("originalStatus")));
        String classification = classificationOf(raw.get("classification"), environment);
        boolean classificationReview = "PRODUCTION".equals(environment) && !"REAL".equals(classification);
        boolean review =
                Boolean.TRUE.equals(raw.get("reviewRequired")) || absent || revision == null || classificationReview;
        String payerKind = payerKindOf(raw.get("payerKind"));
        String payerLabel = clipField(text(raw.get("payerLabel")), 200);
        if (payerLabel == null) {
            payerKind = payerKind == null ? "ABSENT" : payerKind;
        }
        return new TransactionView(
                UUID.randomUUID(),
                scope.companyId(),
                environment,
                transactionId,
                first(text(raw.get("orderReference")), transactionId),
                clipField(text(raw.get("processorReference")), 80),
                text(raw.get("originalStatus")),
                normalized,
                amount,
                currency,
                absent,
                paid,
                paidAbsent,
                review,
                Boolean.TRUE.equals(raw.get("testLabeled")),
                classification,
                clipField(text(raw.get("classificationReason")), 240),
                clipField(text(raw.get("commercialApplication")), 80),
                clipField(text(raw.get("commercialDescription")), 200),
                payerKind,
                payerLabel,
                clipField(text(raw.get("payerProvenance")), 40),
                clipField(text(raw.get("paymentMethod")), 40),
                clipField(text(raw.get("processorName")), 40),
                clipField(text(raw.get("providerStatus")), 40),
                PayReceiptViews.pendingKind(normalized, paidAbsent, review, classification),
                created,
                updated,
                revision,
                runId,
                correlationId,
                now);
    }

    static boolean shouldApply(TransactionView stored, TransactionView incoming) {
        if (incoming.originRevision() == null) {
            return stored.originRevision() == null && enriches(stored, incoming);
        }
        if (stored.originRevision() == null) {
            return true;
        }
        if (incoming.originRevision().isBefore(stored.originRevision())) {
            return false;
        }
        return observationChanged(stored, merge(stored, incoming));
    }

    static TransactionView merge(TransactionView stored, TransactionView incoming) {
        boolean newer =
                stored.originRevision() == null
                        || (incoming.originRevision() != null
                                && incoming.originRevision().isAfter(stored.originRevision()));
        String paid =
                incoming.paidAmountMinor() != null && (stored.paidAmountMinor() == null || newer)
                        ? incoming.paidAmountMinor()
                        : stored.paidAmountMinor();
        boolean paidAbsent = paid == null;
        String classification = chooseClassification(stored, incoming, newer);
        String classificationReason =
                classification != null && classification.equals(incoming.classification())
                        ? first(incoming.classificationReason(), stored.classificationReason())
                        : stored.classificationReason();
        boolean review = incoming.reviewRequired() || stored.reviewRequired();
        String normalized = first(incoming.normalizedStatus(), stored.normalizedStatus());
        boolean incomingPayerKnown =
                "EMAIL".equals(incoming.payerKind()) || "SUBJECT".equals(incoming.payerKind());
        String payerKind = incomingPayerKnown ? incoming.payerKind() : first(stored.payerKind(), incoming.payerKind());
        String payerLabel = incomingPayerKnown ? first(incoming.payerLabel(), stored.payerLabel()) : stored.payerLabel();
        String payerProvenance =
                incomingPayerKnown ? first(incoming.payerProvenance(), stored.payerProvenance()) : stored.payerProvenance();
        return new TransactionView(
                stored.id(),
                incoming.companyId(),
                incoming.environment(),
                incoming.transactionId(),
                first(incoming.orderReference(), stored.orderReference()),
                first(incoming.processorReference(), stored.processorReference()),
                first(incoming.originalStatus(), stored.originalStatus()),
                normalized,
                first(incoming.amountMinor(), stored.amountMinor()),
                first(incoming.currency(), stored.currency()),
                incoming.amountMinor() == null && stored.amountMinor() == null,
                paid,
                paidAbsent,
                review,
                incoming.testLabeled() || stored.testLabeled(),
                classification,
                classificationReason,
                first(incoming.commercialApplication(), stored.commercialApplication()),
                first(incoming.commercialDescription(), stored.commercialDescription()),
                payerKind,
                payerLabel,
                payerProvenance,
                first(incoming.paymentMethod(), stored.paymentMethod()),
                first(incoming.processorName(), stored.processorName()),
                first(incoming.providerStatus(), stored.providerStatus()),
                PayReceiptViews.pendingKind(normalized, paidAbsent, review, classification),
                firstInstant(incoming.originCreatedAt(), stored.originCreatedAt()),
                firstInstant(incoming.originUpdatedAt(), stored.originUpdatedAt()),
                firstInstant(incoming.originRevision(), stored.originRevision()),
                incoming.lastSyncRunId(),
                incoming.lastCorrelationId(),
                incoming.updatedAt());
    }

    private static boolean enriches(TransactionView stored, TransactionView incoming) {
        return filled(stored.paidAmountMinor(), incoming.paidAmountMinor())
                || filled(stored.payerLabel(), incoming.payerLabel())
                || filled(stored.paymentMethod(), incoming.paymentMethod())
                || filled(stored.commercialApplication(), incoming.commercialApplication())
                || filled(stored.commercialDescription(), incoming.commercialDescription())
                || filled(stored.processorName(), incoming.processorName())
                || filled(stored.processorReference(), incoming.processorReference())
                || (stored.paidAmountAbsent() && !incoming.paidAmountAbsent());
    }

    private static boolean filled(String stored, String incoming) {
        return (stored == null || stored.isBlank()) && incoming != null && !incoming.isBlank();
    }

    private static String payerKindOf(Object raw) {
        String value = text(raw);
        if (value != null && List.of("EMAIL", "SUBJECT", "ABSENT").contains(value)) {
            return value;
        }
        return null;
    }

    private static String clipField(String value, int max) {
        if (value == null || value.isBlank() || "null".equals(value)) {
            return null;
        }
        return value.length() > max ? value.substring(0, max) : value;
    }

    private static Instant firstInstant(Instant left, Instant fallback) {
        return left == null ? fallback : left;
    }

    private String resolveEnvironment(AuthorizedScope scope, String requested) {
        String mapped =
                receipts.authorizedEnvironment(scope)
                        .orElseThrow(() -> ValidationException.of("companyId", "Empresa sem vínculo autorizado com o ActionHub Pay."));
        if (requested != null && !requested.isBlank() && !mapped.equalsIgnoreCase(requested)) {
            throw ValidationException.of("environment", "Ambiente incompatível com o vínculo autorizado desta empresa.");
        }
        return mapped;
    }

    private void requireReceiptSync() {
        if (!properties.getIntegration().isReceiptSyncAllowed()) {
            throw new SecurityException("write-forbidden");
        }
    }

    private SyncRunView withMonitor(SyncRunView run) {
        String base = properties.getIntegration().getSpiderMonitorBaseUrl();
        if (base == null || base.isBlank() || run == null) {
            return run;
        }
        if (run.spiderMessageId() == null || run.spiderMessageId().isBlank()) {
            return run;
        }
        String trimmed = base.endsWith("/") ? base.substring(0, base.length() - 1) : base;
        String url = trimmed + "/?q=" + run.spiderMessageId() + "&execution=" + run.spiderMessageId();
        return new SyncRunView(
                run.id(),
                run.environment(),
                run.status(),
                run.rootCorrelationId(),
                run.spiderMessageId(),
                run.resumeCursor(),
                run.pageCount(),
                run.importedCount(),
                run.updatedCount(),
                run.reviewCount(),
                run.lastError(),
                run.startedAt(),
                run.finishedAt(),
                url);
    }

    private static String normalizeStatus(String normalized, String original) {
        if (normalized != null && List.of("IN_PROGRESS", "CONFIRMED", "REFUSED", "REFUNDED", "REVIEW_REQUIRED", "UNKNOWN").contains(normalized)) {
            return normalized;
        }
        String status = original == null ? "" : original.toUpperCase();
        return switch (status) {
            case "PAID" -> "CONFIRMED";
            case "PENDING" -> "IN_PROGRESS";
            case "CANCELLED", "CANCELED" -> "REFUSED";
            case "REFUNDED" -> "REFUNDED";
            default -> "REVIEW_REQUIRED";
        };
    }

    private static String amountMinor(Object raw) {
        if (raw == null) {
            return null;
        }
        String text = String.valueOf(raw).trim();
        if (!text.matches("[0-9]+") || text.length() > 19) {
            return null;
        }
        return text;
    }

    private static String currency(Object raw) {
        if (raw == null) {
            return null;
        }
        String text = String.valueOf(raw).trim().toUpperCase();
        return text.matches("[A-Z]{3}") ? text : null;
    }

    private static Instant parseInstant(Object raw) {
        if (raw == null) {
            return null;
        }
        try {
            return Instant.parse(String.valueOf(raw));
        } catch (RuntimeException ignored) {
            return null;
        }
    }

    private static String text(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    private static String chooseClassification(TransactionView stored, TransactionView incoming, boolean newer) {
        String next = incoming.classification();
        String current = stored.classification();
        if (next == null || next.isBlank()) {
            return current;
        }
        if (current == null || current.isBlank() || "INDETERMINATE".equals(current) || newer) {
            return next;
        }
        return current;
    }

    private static boolean observationChanged(TransactionView stored, TransactionView merged) {
        return !java.util.Objects.equals(stored.normalizedStatus(), merged.normalizedStatus())
                || !java.util.Objects.equals(stored.originalStatus(), merged.originalStatus())
                || !java.util.Objects.equals(stored.amountMinor(), merged.amountMinor())
                || !java.util.Objects.equals(stored.paidAmountMinor(), merged.paidAmountMinor())
                || !java.util.Objects.equals(stored.classification(), merged.classification())
                || !java.util.Objects.equals(stored.classificationReason(), merged.classificationReason())
                || !java.util.Objects.equals(stored.commercialApplication(), merged.commercialApplication())
                || !java.util.Objects.equals(stored.commercialDescription(), merged.commercialDescription())
                || !java.util.Objects.equals(stored.payerKind(), merged.payerKind())
                || !java.util.Objects.equals(stored.payerLabel(), merged.payerLabel())
                || !java.util.Objects.equals(stored.paymentMethod(), merged.paymentMethod())
                || !java.util.Objects.equals(stored.processorName(), merged.processorName())
                || stored.paidAmountAbsent() != merged.paidAmountAbsent();
    }

    private static String first(String left, String fallback) {
        return left == null || left.isBlank() ? fallback : left;
    }

    private static String clip(String value) {
        if (value == null) {
            return "Falha na sincronização.";
        }
        return value.length() > 200 ? value.substring(0, 200) : value;
    }

    private SyncResult resultOf(AuthorizedScope scope, String environment, UUID runId, boolean resumed) {
        return new SyncResult(
                withMonitor(receipts.findRun(scope, runId).orElseThrow()),
                receipts.list(scope, environment, 200),
                receipts.listReviews(scope, environment, 200),
                resumed,
                false);
    }

    private static String firstTransactionId(SpiderListResult page) {
        if (page.items() != null && !page.items().isEmpty()) {
            return text(page.items().getFirst().get("transactionId"));
        }
        if (page.reviews() != null && !page.reviews().isEmpty()) {
            return text(page.reviews().getFirst().get("transactionId"));
        }
        return null;
    }

    private static String classificationOf(Object raw, String environment) {
        String value = text(raw);
        if (value != null && List.of("REAL", "TEST", "INDETERMINATE").contains(value)) {
            return value;
        }
        return "PRODUCTION".equals(environment) ? "INDETERMINATE" : "TEST";
    }

    private record ApplyCounts(int imported, int updated, int review, Instant lastOriginUpdatedAt, String lastTransactionId) {}
}
