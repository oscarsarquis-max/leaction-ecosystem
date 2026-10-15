package br.com.actionfinance.application.integration;

import org.junit.jupiter.api.Test;

import java.time.Instant;
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
                PayReceiptViews.pendingKind(normalized, paid == null, false, classification),
                revision,
                revision,
                revision,
                UUID.fromString("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
                "corr-synthetic",
                revision);
    }
}
