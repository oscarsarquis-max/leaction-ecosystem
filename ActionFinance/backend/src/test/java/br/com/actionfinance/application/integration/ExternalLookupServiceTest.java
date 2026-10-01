package br.com.actionfinance.application.integration;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.finance.AuthorizedScope;
import br.com.actionfinance.application.finance.CompanyAccessService;
import br.com.actionfinance.application.finance.FinanceExceptions.BindingConflictException;
import br.com.actionfinance.application.finance.FinanceExceptions.IdempotencyConflictException;
import br.com.actionfinance.application.finance.TitleService;
import br.com.actionfinance.application.finance.TitleView;
import br.com.actionfinance.configuration.ActionFinanceProperties;
import br.com.actionfinance.domain.TitleDirection;
import br.com.actionfinance.infrastructure.persistence.JdbcExternalOperationRepository;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class ExternalLookupServiceTest {

    private static final UUID COMPANY = UUID.fromString("11111111-1111-4111-a111-111111111111");
    private static final UUID TITLE = UUID.fromString("11111111-cccc-4111-a111-111111111301");
    private static final UUID OTHER_TITLE = UUID.fromString("11111111-cccc-4111-a111-111111111302");
    private static final UUID TENANT = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0001");

    @Test
    void transportFailureKeepsAwaitingObservation() {
        RecordingSpider spider = new RecordingSpider(SpiderInteractionClient.SpiderLookupResult.unavailable("afc-1", "down"));
        ExternalLookupService service = service(true, spider, true, Optional.empty(), Optional.empty());
        ExternalLookupView view =
                service.consult(principal(), COMPANY, TitleDirection.RECEIVABLE, TITLE, "pay-homolog-0001");
        assertThat(view.externalStatus()).isEqualTo("AWAITING_SEND");
        assertThat(view.lastAttemptOutcome()).isEqualTo("UNAVAILABLE");
        assertThat(view.automaticSettlement()).isFalse();
        assertThat(spider.calls).hasSize(1);
    }

    @Test
    void identicalRetryRequeriesAndKeepsSameOperationIdentity() {
        RecordingSpider spider = new RecordingSpider(ready());
        AtomicReference<ExternalLookupView> stored = new AtomicReference<>();
        JdbcExternalOperationRepository operations = operations(true, Optional.empty(), Optional.empty(), stored);
        ExternalLookupService service = service(true, spider, true, operations);
        ExternalLookupView first =
                service.consult(principal(), COMPANY, TitleDirection.RECEIVABLE, TITLE, "pay-homolog-0001");
        ExternalLookupView second =
                service.consult(principal(), COMPANY, TitleDirection.RECEIVABLE, TITLE, "pay-homolog-0001");
        assertThat(spider.calls).hasSize(2);
        assertThat(second.id()).isEqualTo(first.id());
        assertThat(second.correlationId()).isEqualTo(first.correlationId());
    }

    @Test
    void otherTitleOnSameReferenceIsConflict() {
        ExternalLookupView bound =
                new ExternalLookupView(
                        UUID.randomUUID(),
                        COMPANY,
                        TITLE,
                        "LOOKUP_ACTIONHUB_PAYMENT",
                        "ACTIONHUB_PAY",
                        "pay-homolog-0001",
                        null,
                        null,
                        "AWAITING_SEND",
                        "PENDING",
                        "afc-1",
                        null,
                        null,
                        null,
                        null,
                        null,
                        null,
                        null,
                        "STARTED",
                        null,
                        0L,
                        false,
                        true);
        TitleService titles = mock(TitleService.class);
        when(titles.get(any(), eq(COMPANY), eq(TitleDirection.RECEIVABLE), any())).thenReturn(mock(TitleView.class));
        ActionFinanceProperties properties = new ActionFinanceProperties();
        properties.getIntegration().setHomolog(true);
        CompanyAccessService companies = mock(CompanyAccessService.class);
        when(companies.requireActiveMembership(any(), eq(COMPANY))).thenReturn(new AuthorizedScope(TENANT, COMPANY));
        ExternalLookupService named =
                new ExternalLookupService(
                        properties,
                        companies,
                        titles,
                        operations(true, Optional.of(bound), Optional.empty(), new AtomicReference<>(bound)),
                        new RecordingSpider(null),
                        passthroughTx(),
                        new LookupConcurrencyGate());
        assertThatThrownBy(
                        () ->
                                named.consult(
                                        principal(), COMPANY, TitleDirection.RECEIVABLE, OTHER_TITLE, "pay-homolog-0001"))
                .isInstanceOf(BindingConflictException.class);
    }

    @Test
    void divergentFingerprintOnSameIdentityIsConflict() {
        ExternalLookupView existing =
                new ExternalLookupView(
                        UUID.randomUUID(),
                        COMPANY,
                        TITLE,
                        "LOOKUP_ACTIONHUB_PAYMENT",
                        "ACTIONHUB_PAY",
                        "pay-homolog-0001",
                        null,
                        null,
                        "AWAITING_SEND",
                        "PENDING",
                        "afc-1",
                        null,
                        null,
                        null,
                        null,
                        null,
                        null,
                        null,
                        "STARTED",
                        null,
                        0L,
                        false,
                        true);
        ExternalLookupService service =
                service(true, new RecordingSpider(null), true, Optional.of(existing), Optional.of("other-fingerprint"));
        assertThatThrownBy(
                        () ->
                                service.consult(
                                        principal(), COMPANY, TitleDirection.RECEIVABLE, TITLE, "pay-homolog-0001"))
                .isInstanceOf(IdempotencyConflictException.class);
    }

    @Test
    void homologOffNeverCallsSpider() {
        RecordingSpider spider = new RecordingSpider(null);
        ExternalLookupService service = service(false, spider, true, Optional.empty(), Optional.empty());
        assertThatThrownBy(
                        () ->
                                service.consult(
                                        principal(), COMPANY, TitleDirection.RECEIVABLE, TITLE, "pay-homolog-0001"))
                .isInstanceOf(SecurityException.class);
        assertThat(spider.calls).isEmpty();
    }

    @Test
    void missingMappingNeverCallsSpider() {
        RecordingSpider spider = new RecordingSpider(null);
        ExternalLookupService service = service(true, spider, false, Optional.empty(), Optional.empty());
        assertThatThrownBy(
                        () ->
                                service.consult(
                                        principal(), COMPANY, TitleDirection.RECEIVABLE, TITLE, "pay-homolog-0001"))
                .hasMessageContaining("vínculo autorizado");
        assertThat(spider.calls).isEmpty();
    }

    @Test
    void revokedMappingHidesReplay() {
        ExternalLookupView bound =
                new ExternalLookupView(
                        UUID.randomUUID(),
                        COMPANY,
                        TITLE,
                        "LOOKUP_ACTIONHUB_PAYMENT",
                        "ACTIONHUB_PAY",
                        "pay-homolog-0001",
                        null,
                        null,
                        "CONFIRMED",
                        "DELIVERED",
                        "afc-1",
                        null,
                        null,
                        null,
                        null,
                        null,
                        null,
                        null,
                        "DELIVERED",
                        null,
                        1L,
                        false,
                        true);
        JdbcExternalOperationRepository operations =
                operations(false, Optional.of(bound), Optional.empty(), new AtomicReference<>(bound));
        ExternalLookupService service = service(true, new RecordingSpider(null), false, operations);
        assertThat(service.current(principal(), COMPANY, TitleDirection.RECEIVABLE, TITLE)).isEmpty();
        verify(operations, never()).findByTitle(any(), any());
    }

    private ExternalLookupService service(
            boolean homolog,
            RecordingSpider spider,
            boolean mapped,
            Optional<ExternalLookupView> existing,
            Optional<String> fingerprint) {
        return service(
                homolog,
                spider,
                mapped,
                operations(mapped, existing, fingerprint, new AtomicReference<>(existing.orElse(null))));
    }

    private ExternalLookupService service(
            boolean homolog,
            RecordingSpider spider,
            boolean mapped,
            JdbcExternalOperationRepository operations) {
        ActionFinanceProperties properties = new ActionFinanceProperties();
        properties.getIntegration().setHomolog(homolog);
        CompanyAccessService companies = mock(CompanyAccessService.class);
        when(companies.requireActiveMembership(any(), eq(COMPANY)))
                .thenReturn(new AuthorizedScope(TENANT, COMPANY));
        TitleService titles = mock(TitleService.class);
        when(titles.get(any(), eq(COMPANY), eq(TitleDirection.RECEIVABLE), any()))
                .thenReturn(mock(TitleView.class));
        return new ExternalLookupService(
                properties, companies, titles, operations, spider, passthroughTx(), new LookupConcurrencyGate());
    }

    private JdbcExternalOperationRepository operations(
            boolean mapped,
            Optional<ExternalLookupView> existing,
            Optional<String> fingerprint,
            AtomicReference<ExternalLookupView> stored) {
        JdbcExternalOperationRepository operations = mock(JdbcExternalOperationRepository.class);
        when(operations.mappingAuthorized(any())).thenReturn(mapped);
        when(operations.findByReference(any(), any())).thenAnswer(invocation -> Optional.ofNullable(stored.get()));
        when(operations.fingerprint(any(), any())).thenReturn(fingerprint);
        when(operations.insertOrGet(any(), any(), any()))
                .thenAnswer(
                        invocation -> {
                            ExternalLookupView view = invocation.getArgument(1);
                            stored.compareAndSet(null, view);
                            return stored.get();
                        });
        when(operations.updateIfVersion(any(), any()))
                .thenAnswer(
                        invocation -> {
                            stored.set(invocation.getArgument(1));
                            return true;
                        });
        when(operations.findById(any(), any())).thenAnswer(invocation -> Optional.ofNullable(stored.get()));
        when(operations.findByTitle(any(), any())).thenAnswer(invocation -> Optional.ofNullable(stored.get()));
        when(operations.openAttemptIds(any(), any(), any())).thenReturn(List.of());
        when(operations.attemptStillOpen(any(), any())).thenReturn(true);
        when(operations.lockOperation(any(), any())).thenAnswer(invocation -> stored.get());
        when(operations.finishAttempt(any(), any(), any(), org.mockito.ArgumentMatchers.anyBoolean(), any(), any()))
                .thenReturn(true);
        when(operations.beginAttempt(any(), any(), any()))
                .thenAnswer(
                        invocation -> {
                            ExternalLookupView operation = invocation.getArgument(1);
                            UUID attemptId = UUID.randomUUID();
                            return new LookupAttemptStart(
                                    attemptId, "afa-" + attemptId, operation, java.time.Instant.now());
                        });
        return operations;
    }

    private static org.springframework.transaction.PlatformTransactionManager passthroughTx() {
        return new org.springframework.transaction.PlatformTransactionManager() {
            @Override
            public org.springframework.transaction.TransactionStatus getTransaction(
                    org.springframework.transaction.TransactionDefinition definition) {
                return new org.springframework.transaction.support.SimpleTransactionStatus();
            }

            @Override
            public void commit(org.springframework.transaction.TransactionStatus status) {}

            @Override
            public void rollback(org.springframework.transaction.TransactionStatus status) {}
        };
    }

    private static SpiderInteractionClient.SpiderLookupResult ready() {
        return new SpiderInteractionClient.SpiderLookupResult(
                true,
                "READY",
                "spd-1",
                "PRESENT_EXTERNAL_LOOKUP",
                "SATELLITE_CONTRACT_V1_3_THEN_CAPABILITY_RESOLUTION",
                "LOOKUP_ACTIONHUB_PAYMENT",
                "afc-1",
                Map.of(
                        "externalStatus",
                        "CONFIRMED",
                        "amountMinor",
                        "12550",
                        "currency",
                        "BRL",
                        "providerReference",
                        "pay-homolog-0001",
                        "origin",
                        "SIMULATOR"),
                null,
                null);
    }

    private static ApplicationPrincipal principal() {
        return mock(ApplicationPrincipal.class);
    }

    private static final class RecordingSpider implements SpiderInteractionClient {
        private final SpiderLookupResult result;
        private final List<LookupCall> calls = new ArrayList<>();

        private RecordingSpider(SpiderLookupResult result) {
            this.result = result;
        }

        @Override
        public SpiderLookupResult lookup(
                String correlationId,
                String idempotencyKey,
                String companyId,
                String titleId,
                String externalReference) {
            calls.add(new LookupCall(correlationId, idempotencyKey, companyId, externalReference));
            if (result == null) {
                return null;
            }
            return new SpiderLookupResult(
                    result.available(),
                    result.status(),
                    result.decisionId(),
                    result.requiredAction(),
                    result.spiderPath(),
                    result.capabilityId(),
                    correlationId,
                    result.summary(),
                    result.errorCode(),
                    result.errorMessage());
        }

        private record LookupCall(
                String correlationId, String idempotencyKey, String companyId, String externalReference) {}
    }
}
