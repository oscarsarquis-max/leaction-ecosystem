package br.com.actionfinance.application.integration;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

public record ExternalLookupView(
        UUID id,
        UUID companyId,
        UUID titleId,
        String capability,
        String originSystem,
        String externalReference,
        BigDecimal amountMinor,
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
        long version,
        boolean automaticSettlement,
        boolean homolog) {

    public ExternalLookupView withLastAttemptId(UUID attemptId) {
        return new ExternalLookupView(
                id,
                companyId,
                titleId,
                capability,
                originSystem,
                externalReference,
                amountMinor,
                currency,
                externalStatus,
                deliveryStatus,
                correlationId,
                spiderDecisionId,
                providerReference,
                providerOrigin,
                lastError,
                observedAt,
                updatedAt,
                lastAttemptAt,
                lastAttemptOutcome,
                attemptId,
                version,
                automaticSettlement,
                homolog);
    }
}
