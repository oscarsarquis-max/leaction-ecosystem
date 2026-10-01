package br.com.actionfinance.application.integration;

import br.com.actionfinance.application.finance.FinanceExceptions.ValidationException;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ExternalLookupRulesTest {

    private static final UUID COMPANY = UUID.fromString("11111111-1111-4111-a111-111111111111");
    private static final UUID TITLE = UUID.fromString("11111111-cccc-4111-a111-111111111301");
    private static final Instant T1 = Instant.parse("2026-09-30T12:00:00Z");
    private static final Instant T0 = Instant.parse("2026-09-30T11:00:00Z");

    @Test
    void timeoutKeepsConfirmedObservation() {
        ExternalLookupView confirmed = confirmed();
        ExternalLookupView after =
                ExternalLookupRules.applyAttempt(
                        confirmed, SpiderInteractionClient.SpiderLookupResult.unavailable("afc-1", "timeout"), T1);
        assertThat(after.externalStatus()).isEqualTo("CONFIRMED");
        assertThat(after.amountMinor()).isEqualByComparingTo("12550");
        assertThat(after.lastAttemptOutcome()).isEqualTo("UNAVAILABLE");
        assertThat(after.deliveryStatus()).isEqualTo("UNAVAILABLE");
        assertThat(after.observedAt()).isEqualTo(confirmed.observedAt());
    }

    @Test
    void divergentAmountRequiresReviewWithoutReplacingConfirmedValue() {
        ExternalLookupView after =
                ExternalLookupRules.applyAttempt(confirmed(), ready("25000", "BRL", "CONFIRMED", "pay-homolog-0001"), T1);
        assertThat(after.externalStatus()).isEqualTo("REVIEW_REQUIRED");
        assertThat(after.amountMinor()).isEqualByComparingTo("12550");
        assertThat(after.lastAttemptOutcome()).isEqualTo("CONFLICT");
        assertThat(after.lastError()).contains("Divergência");
    }

    @Test
    void refundedCanFollowConfirmed() {
        ExternalLookupView after =
                ExternalLookupRules.applyAttempt(confirmed(), ready("12550", "BRL", "REFUNDED", "pay-homolog-0001"), T1);
        assertThat(after.externalStatus()).isEqualTo("REFUNDED");
        assertThat(after.amountMinor()).isEqualByComparingTo("12550");
        assertThat(after.lastAttemptOutcome()).isEqualTo("DELIVERED");
    }

    @Test
    void wrongReferenceIsInvalidAndKeepsObservation() {
        ExternalLookupView after =
                ExternalLookupRules.applyAttempt(confirmed(), ready("12550", "BRL", "CONFIRMED", "outra-ref"), T1);
        assertThat(after.externalStatus()).isEqualTo("CONFIRMED");
        assertThat(after.lastAttemptOutcome()).isEqualTo("INVALID");
        assertThat(after.deliveryStatus()).isEqualTo("CONFLICT");
    }

    @Test
    void staleProviderTimestampDoesNotReplaceNewerObservation() {
        ExternalLookupView newer =
                new ExternalLookupView(
                        confirmed().id(),
                        COMPANY,
                        TITLE,
                        "LOOKUP_ACTIONHUB_PAYMENT",
                        "ACTIONHUB_PAY",
                        "pay-homolog-0001",
                        new BigDecimal("12550"),
                        "BRL",
                        "CONFIRMED",
                        "DELIVERED",
                        "afc-1",
                        "spd-2",
                        "pay-homolog-0001",
                        "SIMULATOR",
                        null,
                        T1,
                        T1,
                        T1,
                        "DELIVERED",
                        null,
                        1L,
                        false,
                        true);
        ExternalLookupView late =
                ExternalLookupRules.applyAttempt(
                        newer,
                        new SpiderInteractionClient.SpiderLookupResult(
                                true,
                                "READY",
                                "spd-old",
                                "PRESENT_EXTERNAL_LOOKUP",
                                "SATELLITE_CONTRACT_V1_3_THEN_CAPABILITY_RESOLUTION",
                                "LOOKUP_ACTIONHUB_PAYMENT",
                                "afc-1",
                                Map.of(
                                        "externalStatus",
                                        "REFUNDED",
                                        "amountMinor",
                                        "12550",
                                        "currency",
                                        "BRL",
                                        "providerReference",
                                        "pay-homolog-0001",
                                        "providerObservedAt",
                                        T0.toString()),
                                null,
                                null),
                        Instant.parse("2026-09-30T13:00:00Z"));
        assertThat(late.externalStatus()).isEqualTo("CONFIRMED");
        assertThat(late.lastAttemptOutcome()).isEqualTo("DELIVERED");
        assertThat(late.lastError()).contains("atrasada");
    }

    @Test
    void rejectsFractionAndOverflow() {
        assertThatThrownBy(() -> ExternalLookupRules.requireAmountMinor("12550.5"))
                .isInstanceOf(ValidationException.class);
        assertThatThrownBy(() -> ExternalLookupRules.requireAmountMinor("10000000000000000000"))
                .isInstanceOf(ValidationException.class);
        assertThatThrownBy(() -> ExternalLookupRules.requireAmountMinor(12.5))
                .isInstanceOf(ValidationException.class);
        assertThat(ExternalLookupRules.requireAmountMinor("12550")).isEqualByComparingTo("12550");
        assertThat(ExternalLookupRules.requireAmountMinor(12550)).isEqualByComparingTo("12550");
    }

    @Test
    void fingerprintIncludesTitleAndRecognizesLegacy() {
        String current = ExternalLookupRules.fingerprint(COMPANY, "pay-homolog-0001", TITLE);
        assertThat(ExternalLookupRules.sameLookupIdentity(current, COMPANY, "pay-homolog-0001", TITLE)).isTrue();
        assertThat(ExternalLookupRules.sameLookupIdentity(current, COMPANY, "pay-homolog-0001", UUID.randomUUID()))
                .isFalse();
    }

    private static ExternalLookupView confirmed() {
        return new ExternalLookupView(
                UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0009"),
                COMPANY,
                TITLE,
                "LOOKUP_ACTIONHUB_PAYMENT",
                "ACTIONHUB_PAY",
                "pay-homolog-0001",
                new BigDecimal("12550"),
                "BRL",
                "CONFIRMED",
                "DELIVERED",
                "afc-1",
                "spd-1",
                "pay-homolog-0001",
                "SIMULATOR",
                null,
                T1,
                T1,
                T1,
                "DELIVERED",
                null,
                1L,
                false,
                true);
    }

    private static SpiderInteractionClient.SpiderLookupResult ready(
            String amount, String currency, String status, String reference) {
        return new SpiderInteractionClient.SpiderLookupResult(
                true,
                "READY",
                "spd-n",
                "PRESENT_EXTERNAL_LOOKUP",
                "SATELLITE_CONTRACT_V1_3_THEN_CAPABILITY_RESOLUTION",
                "LOOKUP_ACTIONHUB_PAYMENT",
                "afc-1",
                Map.of(
                        "externalStatus",
                        status,
                        "amountMinor",
                        amount,
                        "currency",
                        currency,
                        "providerReference",
                        reference,
                        "origin",
                        "SIMULATOR"),
                null,
                null);
    }
}
