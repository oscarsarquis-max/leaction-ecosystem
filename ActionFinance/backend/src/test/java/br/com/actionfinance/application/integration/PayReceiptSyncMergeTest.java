package br.com.actionfinance.application.integration;

import br.com.actionfinance.application.finance.AuthorizedScope;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PayReceiptSyncMergeTest {

    private static final Instant REV = Instant.parse("2026-10-06T15:01:49.498Z");
    private static final UUID COMPANY = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final String TXN = "11111111-2222-4333-8444-555555555555";

    @Test
    void omissionKeepsConfirmedPaidAndCommercialIdentity() {
        var stored = view("9000", "8000", "REAL", "CONFIRMED", "lojadepaes", "EMAIL", "cliente@exemplo.test", REV);
        var incoming = view("9000", null, "REAL", "CONFIRMED", null, "ABSENT", null, REV);
        var merged = PayReceiptSyncService.merge(stored, incoming);
        assertEquals("9000", merged.amountMinor());
        assertEquals("8000", merged.paidAmountMinor());
        assertFalse(merged.paidAmountAbsent());
        assertEquals("lojadepaes", merged.commercialApplication());
        assertEquals("EMAIL", merged.payerKind());
        assertEquals("cliente@exemplo.test", merged.payerLabel());
        assertFalse(PayReceiptSyncService.shouldApply(stored, incoming));
    }

    @Test
    void newerOmissionDoesNotRevokePaid() {
        var stored = view("9000", "8000", "REAL", "CONFIRMED", "lojadepaes", "EMAIL", "cliente@exemplo.test", REV);
        var incoming = view("9000", null, "REAL", "CONFIRMED", "lojadepaes", "EMAIL", "cliente@exemplo.test", REV.plusSeconds(1));
        assertFalse(PayReceiptSyncService.shouldApply(stored, incoming));
        assertEquals("8000", PayReceiptSyncService.merge(stored, incoming).paidAmountMinor());
    }

    @Test
    void sameRevisionFillsGapsWithoutCopyingChargedIntoPaid() {
        var stored = view("9000", null, "INDETERMINATE", "CONFIRMED", null, null, null, REV);
        var incoming = view("9000", null, "REAL", "CONFIRMED", "lojadepaes", "EMAIL", "cliente@exemplo.test", REV);
        assertTrue(PayReceiptSyncService.shouldApply(stored, incoming));
        var merged = PayReceiptSyncService.merge(stored, incoming);
        assertEquals("9000", merged.amountMinor());
        assertNull(merged.paidAmountMinor());
        assertTrue(merged.paidAmountAbsent());
        assertEquals("lojadepaes", merged.commercialApplication());
        assertEquals("REAL", merged.classification());
        assertEquals("PAID_AMOUNT_MISSING", merged.pendingKind());
    }

    @Test
    void sameRevisionDoesNotReplaceAConfirmedPaid() {
        var stored = view("9000", "8000", "REAL", "CONFIRMED", null, null, null, REV);
        var incoming = view("9000", "9000", "REAL", "CONFIRMED", null, null, null, REV);
        assertFalse(PayReceiptSyncService.shouldApply(stored, incoming));
        assertEquals("8000", PayReceiptSyncService.merge(stored, incoming).paidAmountMinor());
    }

    @Test
    void newerDigitsMayReplacePaid() {
        var stored = view("9000", "8000", "REAL", "CONFIRMED", null, null, null, REV);
        var incoming = view("9000", "7500", "REAL", "CONFIRMED", null, null, null, REV.plusSeconds(5));
        assertTrue(PayReceiptSyncService.shouldApply(stored, incoming));
        assertEquals("7500", PayReceiptSyncService.merge(stored, incoming).paidAmountMinor());
        assertEquals("9000", PayReceiptSyncService.merge(stored, incoming).amountMinor());
    }

    @Test
    void olderResponseDoesNotReplaceStoredFacts() {
        var stored = view("9000", "8000", "REAL", "CONFIRMED", "lojadepaes", "EMAIL", "cliente@exemplo.test", REV);
        var incoming = view("100", "100", "TEST", "REFUSED", "outro", "SUBJECT", "subj-1", REV.minusSeconds(60));
        assertFalse(PayReceiptSyncService.shouldApply(stored, incoming));
    }

    @Test
    void indeterminateDoesNotDowngradeAProvenClassification() {
        var stored = view("9000", null, "REAL", "CONFIRMED", null, null, null, REV);
        var incoming = view("9000", null, "INDETERMINATE", "CONFIRMED", null, null, null, REV);
        assertEquals("REAL", PayReceiptSyncService.merge(stored, incoming).classification());
        assertFalse(PayReceiptSyncService.shouldApply(stored, incoming));
    }

    @Test
    void repeatingTheSameObservationDoesNotApply() {
        var stored = view("9000", null, "INDETERMINATE", "CONFIRMED", null, "ABSENT", null, REV);
        var incoming = view("9000", null, "INDETERMINATE", "CONFIRMED", null, "ABSENT", null, REV);
        assertFalse(PayReceiptSyncService.shouldApply(stored, incoming));
    }

    @Test
    void absentPayerIsRecordedOnlyWhenNothingWasKnown() {
        var stored = view("9000", null, "INDETERMINATE", "CONFIRMED", null, null, null, REV);
        var incoming = view("9000", null, "INDETERMINATE", "CONFIRMED", null, "ABSENT", null, REV);
        assertTrue(PayReceiptSyncService.shouldApply(stored, incoming));
        assertEquals("ABSENT", PayReceiptSyncService.merge(stored, incoming).payerKind());
    }

    @Test
    void pendingKindsStayDistinct() {
        assertEquals("ENVIRONMENT_UNPROVEN", PayReceiptViews.pendingKind("CONFIRMED", true, false, "INDETERMINATE"));
        assertEquals("PAID_AMOUNT_MISSING", PayReceiptViews.pendingKind("CONFIRMED", true, false, "REAL"));
        assertEquals("PAID_AMOUNT_MISSING", PayReceiptViews.pendingKind("CONFIRMED", true, false, "TEST"));
        assertEquals("UNPAID_EXPECTED", PayReceiptViews.pendingKind("IN_PROGRESS", true, false, "REAL"));
        assertEquals("UNPAID_EXPECTED", PayReceiptViews.pendingKind("REFUSED", true, false, "REAL"));
        assertEquals("UNPAID_EXPECTED", PayReceiptViews.pendingKind("REFUNDED", true, false, "TEST"));
        assertEquals("NONE", PayReceiptViews.pendingKind("CONFIRMED", false, false, "REAL"));
    }

    @Test
    void listedPayerFieldsAreStoredAsReceivedAndTechnicalEmailIsDropped() {
        Map<String, Object> raw = new LinkedHashMap<>();
        raw.put("transactionId", TXN);
        raw.put("normalizedStatus", "CONFIRMED");
        raw.put("originalStatus", "approved");
        raw.put("amountMinor", "9000");
        raw.put("currency", "BRL");
        raw.put("originRevision", REV.toString());
        raw.put("payerName", "Pagador Exemplo");
        raw.put("payerEmail", "  ");
        raw.put("storeOrderReference", "PED-1042");
        raw.put("storePaymentRequestId", "req-77");
        raw.put("processorPaymentId", "mp-1");
        raw.put("processorApprovedAt", "2026-11-09T18:04:11Z");
        raw.put("processorInstallments", 2);
        raw.put("purchaseDescription", "Fornada de sábado");
        Logger logger = (Logger) LoggerFactory.getLogger(PayReceiptSyncService.class);
        ListAppender<ILoggingEvent> appender = new ListAppender<>();
        appender.start();
        logger.addAppender(appender);
        PayReceiptViews.TransactionView mapped;
        try {
            mapped =
                    PayReceiptSyncService.toView(
                            new AuthorizedScope(COMPANY, COMPANY),
                            "PRODUCTION",
                            UUID.fromString("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
                            "corr-synthetic",
                            raw,
                            REV);
        } finally {
            logger.detachAppender(appender);
        }
        assertEquals("Pagador Exemplo", mapped.payerName());
        assertNull(mapped.payerEmail());
        assertEquals("PED-1042", mapped.storeOrderReference());
        assertEquals("req-77", mapped.storePaymentRequestId());
        assertEquals("mp-1", mapped.processorPaymentId());
        assertEquals("2026-11-09T18:04:11Z", mapped.processorApprovedAt());
        assertEquals(2, mapped.processorInstallments());
        assertEquals("Fornada de sábado", mapped.purchaseDescription());
        String logs = appender.list.stream().map(ILoggingEvent::getFormattedMessage).reduce("", String::concat);
        assertFalse(logs.contains("Pagador Exemplo"));
        assertFalse(logs.contains("Fornada"));

        raw.put("payerEmail", "Loja@Amount.Hub.Local");
        assertNull(
                PayReceiptSyncService.toView(
                                new AuthorizedScope(COMPANY, COMPANY), "PRODUCTION", mapped.lastSyncRunId(), "corr-synthetic", raw, REV)
                        .payerEmail());
    }

    @Test
    void incomingNullPayerFieldsDoNotEraseStoredValues() {
        var stored = view("9000", "8000", "REAL", "CONFIRMED", "lojadepaes", "EMAIL", "cliente@exemplo.test", REV);
        stored =
                new PayReceiptViews.TransactionView(
                        stored.id(),
                        stored.companyId(),
                        stored.environment(),
                        stored.transactionId(),
                        stored.orderReference(),
                        stored.processorReference(),
                        stored.originalStatus(),
                        stored.normalizedStatus(),
                        stored.amountMinor(),
                        stored.currency(),
                        stored.amountAbsent(),
                        stored.paidAmountMinor(),
                        stored.paidAmountAbsent(),
                        stored.reviewRequired(),
                        stored.testLabeled(),
                        stored.classification(),
                        stored.classificationReason(),
                        stored.commercialApplication(),
                        stored.commercialDescription(),
                        stored.payerKind(),
                        stored.payerLabel(),
                        stored.payerProvenance(),
                        "Pagador Exemplo",
                        "pagador.exemplo@exemplo.test",
                        "PED-1042",
                        "req-77",
                        "mp-1",
                        "2026-11-09T18:04:11Z",
                        2,
                        "Fornada de sábado",
                        stored.paymentMethod(),
                        stored.processorName(),
                        stored.providerStatus(),
                        stored.pendingKind(),
                        stored.originCreatedAt(),
                        stored.originUpdatedAt(),
                        stored.originRevision(),
                        stored.lastSyncRunId(),
                        stored.lastCorrelationId(),
                        stored.updatedAt());
        var incoming = view("9000", "8000", "REAL", "CONFIRMED", "lojadepaes", "EMAIL", "cliente@exemplo.test", REV.plusSeconds(1));
        var merged = PayReceiptSyncService.merge(stored, incoming);
        assertEquals("Pagador Exemplo", merged.payerName());
        assertEquals("pagador.exemplo@exemplo.test", merged.payerEmail());
        assertEquals("PED-1042", merged.storeOrderReference());
        assertEquals("req-77", merged.storePaymentRequestId());
        assertEquals("mp-1", merged.processorPaymentId());
        assertEquals("2026-11-09T18:04:11Z", merged.processorApprovedAt());
        assertEquals(2, merged.processorInstallments());
        assertEquals("Fornada de sábado", merged.purchaseDescription());
        assertEquals("EMAIL", merged.payerKind());
        assertEquals("cliente@exemplo.test", merged.payerLabel());
        assertFalse(PayReceiptSyncService.shouldApply(stored, incoming));
    }

    private static PayReceiptViews.TransactionView view(
            String charged,
            String paid,
            String classification,
            String normalized,
            String application,
            String payerKind,
            String payerLabel,
            Instant revision) {
        return new PayReceiptViews.TransactionView(
                UUID.fromString("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"),
                COMPANY,
                "PRODUCTION",
                TXN,
                TXN,
                null,
                "approved",
                normalized,
                charged,
                "BRL",
                charged == null,
                paid,
                paid == null,
                false,
                false,
                classification,
                classification,
                application,
                null,
                payerKind,
                payerLabel,
                payerKind == null ? null : "ACTIONHUB_PAY",
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                PayReceiptViews.pendingKind(normalized, paid == null, false, classification),
                revision,
                revision,
                revision,
                UUID.fromString("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
                "corr-synthetic",
                revision);
    }
}
