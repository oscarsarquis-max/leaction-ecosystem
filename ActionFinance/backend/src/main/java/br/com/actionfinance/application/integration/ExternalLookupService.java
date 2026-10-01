package br.com.actionfinance.application.integration;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.finance.AuthorizedScope;
import br.com.actionfinance.application.finance.CompanyAccessService;
import br.com.actionfinance.application.finance.FinanceExceptions.BindingConflictException;
import br.com.actionfinance.application.finance.FinanceExceptions.IdempotencyConflictException;
import br.com.actionfinance.application.finance.FinanceExceptions.ValidationException;
import br.com.actionfinance.application.finance.TitleService;
import br.com.actionfinance.application.identity.FinancePermissions;
import br.com.actionfinance.configuration.ActionFinanceProperties;
import br.com.actionfinance.domain.TitleDirection;
import br.com.actionfinance.infrastructure.persistence.JdbcExternalOperationRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Duration;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

@Service
public class ExternalLookupService {

    private final ActionFinanceProperties properties;
    private final CompanyAccessService companies;
    private final TitleService titles;
    private final JdbcExternalOperationRepository operations;
    private final SpiderInteractionClient spider;
    private final TransactionTemplate shortTx;
    private final LookupConcurrencyGate gate;

    public ExternalLookupService(
            ActionFinanceProperties properties,
            CompanyAccessService companies,
            TitleService titles,
            JdbcExternalOperationRepository operations,
            SpiderInteractionClient spider,
            PlatformTransactionManager transactions,
            LookupConcurrencyGate gate) {
        this.properties = properties;
        this.companies = companies;
        this.titles = titles;
        this.operations = operations;
        this.spider = spider;
        this.gate = gate;
        this.shortTx = new TransactionTemplate(transactions);
        this.shortTx.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
    }

    public Optional<ExternalLookupView> current(
            ApplicationPrincipal principal, UUID companyId, TitleDirection direction, UUID titleId) {
        if (!properties.getIntegration().isHomolog()) {
            return Optional.empty();
        }
        AuthorizedScope scope = companies.requireActiveMembership(principal, companyId);
        titles.get(principal, companyId, direction, titleId);
        if (!operations.mappingAuthorized(scope)) {
            return Optional.empty();
        }
        Optional<ExternalLookupView> found = operations.findByTitle(scope, titleId);
        found.ifPresent(
                view -> {
                    gate.afterReadForRecover(view.id());
                    gate.beforeRecover(view.id());
                    recoverStale(scope, view.id());
                    gate.afterRecover(view.id());
                });
        return operations.findByTitle(scope, titleId);
    }

    public ExternalLookupView consult(
            ApplicationPrincipal principal,
            UUID companyId,
            TitleDirection direction,
            UUID titleId,
            String externalReference) {
        if (!properties.getIntegration().isHomolog()) {
            throw new SecurityException("company-forbidden");
        }
        companies.requirePermission(principal, companyId, FinancePermissions.TITLES_READ);
        AuthorizedScope scope = companies.requireActiveMembership(principal, companyId);
        titles.get(principal, companyId, direction, titleId);
        if (!operations.mappingAuthorized(scope)) {
            throw ValidationException.of(
                    "companyId", "Esta empresa não tem vínculo autorizado com o ActionHub Pay.");
        }
        String reference = normalizeReference(externalReference);
        String fingerprint = ExternalLookupRules.fingerprint(companyId, reference, titleId);
        ExternalLookupView located = locateOrCreate(scope, companyId, titleId, reference, fingerprint);
        recoverStale(scope, located.id());
        ExternalLookupView current = operations.findById(scope, located.id()).orElse(located);
        LookupAttemptStart start =
                shortTx.execute(status -> operations.beginAttempt(scope, current, Instant.now()));
        if (start == null) {
            throw new IllegalStateException("attempt");
        }
        gate.afterBeginAttempt(start.attemptId());
        SpiderInteractionClient.SpiderLookupResult result =
                spider.lookup(
                        start.attemptCorrelationId(),
                        "lookup-" + start.attemptId(),
                        companyId.toString(),
                        titleId.toString(),
                        reference);
        gate.beforeComplete(start.attemptId());
        return shortTx.execute(status -> complete(scope, start, result));
    }

    private ExternalLookupView complete(
            AuthorizedScope scope, LookupAttemptStart start, SpiderInteractionClient.SpiderLookupResult result) {
        operations.lockOperation(scope, start.operation().id());
        if (!operations.attemptStillOpen(scope, start.attemptId())) {
            return operations.findById(scope, start.operation().id()).orElse(start.operation());
        }
        ExternalLookupView latest = operations.findById(scope, start.operation().id()).orElse(start.operation());
        ExternalLookupView proposed =
                ExternalLookupRules.applyAttempt(latest, result, start.startedAt(), start.attemptCorrelationId())
                        .withLastAttemptId(start.attemptId());
        boolean wrote = operations.updateIfVersion(scope, proposed);
        String discarded = null;
        boolean observationApplied = false;
        if (!wrote) {
            ExternalLookupView again = operations.findById(scope, latest.id()).orElse(latest);
            ExternalLookupView retry =
                    ExternalLookupRules.applyAttempt(again, result, start.startedAt(), start.attemptCorrelationId())
                            .withLastAttemptId(start.attemptId());
            if (ExternalLookupRules.staleObservation(again.observedAt(), retry.observedAt())
                    || !newerObservationAllowed(again, retry)) {
                discarded = "CONCURRENT";
                operations.finishAttempt(
                        scope, start.attemptId(), proposed.lastAttemptOutcome(), false, discarded, Instant.now());
                return again;
            }
            wrote = operations.updateIfVersion(scope, retry);
            if (wrote) {
                observationApplied = ExternalLookupRules.financialChanged(again, retry);
            } else {
                discarded = "CONCURRENT";
            }
            operations.finishAttempt(
                    scope,
                    start.attemptId(),
                    retry.lastAttemptOutcome(),
                    observationApplied,
                    discarded,
                    Instant.now());
            return operations.findById(scope, latest.id()).orElse(again);
        }
        observationApplied = ExternalLookupRules.financialChanged(latest, proposed);
        if (!observationApplied && proposed.lastError() != null && proposed.lastError().contains("atrasada")) {
            discarded = "STALE";
        }
        operations.finishAttempt(
                scope, start.attemptId(), proposed.lastAttemptOutcome(), observationApplied, discarded, Instant.now());
        return operations.findById(scope, latest.id()).orElse(proposed);
    }

    private static boolean newerObservationAllowed(ExternalLookupView stored, ExternalLookupView incoming) {
        return stored.observedAt() == null
                || incoming.observedAt() == null
                || !incoming.observedAt().isBefore(stored.observedAt());
    }

    private void recoverStale(AuthorizedScope scope, UUID operationId) {
        if (gate.recoverSuppressed()) {
            return;
        }
        Duration staleAfter = properties.getIntegration().getLookupStaleAfter();
        if (staleAfter == null || staleAfter.isNegative()) {
            return;
        }
        Instant threshold = Instant.now().minus(staleAfter);
        shortTx.executeWithoutResult(
                status -> {
                    operations.lockOperation(scope, operationId);
                    Instant recoveredAt = Instant.now();
                    for (UUID attemptId : operations.openAttemptIds(scope, operationId, threshold)) {
                        boolean closed =
                                operations.finishAttempt(
                                        scope, attemptId, "UNAVAILABLE", false, "RECOVERED", recoveredAt);
                        if (closed) {
                            operations.markRecoveredIfCurrentAttempt(
                                    scope, operationId, attemptId, threshold, recoveredAt);
                        }
                    }
                });
    }

    private ExternalLookupView locateOrCreate(
            AuthorizedScope scope, UUID companyId, UUID titleId, String reference, String fingerprint) {
        Optional<ExternalLookupView> existing = operations.findByReference(scope, reference);
        if (existing.isPresent()) {
            ExternalLookupView found = existing.get();
            refuseForeignTitle(found, titleId);
            Optional<String> stored = operations.fingerprint(scope, reference);
            if (stored.isPresent() && !ExternalLookupRules.sameLookupIdentity(stored.get(), companyId, reference, titleId)) {
                throw new IdempotencyConflictException();
            }
            if (stored.isPresent() && !stored.get().equals(fingerprint)) {
                operations.upgradeFingerprint(scope, found.id(), fingerprint);
            }
            return found;
        }
        Instant now = Instant.now();
        ExternalLookupView created =
                operations.insertOrGet(
                        scope,
                        new ExternalLookupView(
                                UUID.randomUUID(),
                                companyId,
                                titleId,
                                "LOOKUP_ACTIONHUB_PAYMENT",
                                "ACTIONHUB_PAY",
                                reference,
                                null,
                                null,
                                "AWAITING_SEND",
                                "PENDING",
                                "afc-" + UUID.randomUUID(),
                                null,
                                null,
                                null,
                                null,
                                null,
                                now,
                                now,
                                "STARTED",
                                null,
                                0L,
                                false,
                                true),
                        fingerprint);
        refuseForeignTitle(created, titleId);
        return created;
    }

    private static void refuseForeignTitle(ExternalLookupView found, UUID titleId) {
        if (found.titleId() != null && !found.titleId().equals(titleId)) {
            throw new BindingConflictException();
        }
    }

    private static String normalizeReference(String value) {
        if (value == null || value.isBlank()) {
            throw ValidationException.of("externalReference", "Informe a referência do pagamento de teste.");
        }
        String trimmed = value.trim();
        if (trimmed.length() < 4 || trimmed.length() > 80) {
            throw ValidationException.of("externalReference", "A referência do pagamento de teste é inválida.");
        }
        return trimmed;
    }
}
