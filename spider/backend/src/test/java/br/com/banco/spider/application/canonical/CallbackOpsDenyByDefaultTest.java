package br.com.banco.spider.application.canonical;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import br.com.banco.spider.application.security.AuthorizationDecision;
import br.com.banco.spider.execution.callback.CallbackOutboxProcessor;
import br.com.banco.spider.execution.callback.CallbackProcessingRecoveryService;
import br.com.banco.spider.execution.callback.CallbackReconciliationProcessor;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryCallbackOutboxStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryCallbackReconciliationStore;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

class CallbackOpsDenyByDefaultTest {

  @Test
  void reconcileDeniedByDefault() {
    CallbackOpsAuthorizationPort deny = (op, actor) -> Mono.just(AuthorizationDecision.DENY);
    CallbackReconciliationProcessor processor =
        new CallbackReconciliationProcessor(
            new InMemoryCallbackReconciliationStore(),
            new br.com.banco.spider.infrastructure.persistence.memory
                .InMemoryCallbackReconciliationAttemptStore(),
            new br.com.banco.spider.infrastructure.persistence.memory
                .InMemoryExecutionCallbackContextStore(),
            new InMemoryCallbackOutboxStore(),
            new br.com.banco.spider.execution.callback.ConfiguredCallbackReconciliationPolicyCatalog(
                java.util.List.of()),
            new br.com.banco.spider.execution.callback.ConfiguredCallbackStatusQueryBindingResolver(
                java.util.Map.of()),
            new br.com.banco.spider.execution.callback.CallbackRedeliveryDecisionService(),
            IdentifierGenerator.fixed(() -> "1"),
            SpiderClock.fixed(Instant.parse("2026-08-21T12:00:00Z")));
    ReconcileCallbackNowUseCase useCase =
        new ReconcileCallbackNowUseCase(
            deny, processor, SpiderClock.fixed(Instant.parse("2026-08-21T12:00:00Z")));
    StepVerifier.create(
            useCase.execute(new ReconcileCallbackNowUseCase.Command("actor", "OPS", "w", 10)))
        .assertNext(
            o -> {
              assertEquals(AuthorizationDecision.DENY, o.decision());
              assertNull(o.batch());
            })
        .verifyComplete();
  }

  @Test
  void recoverDeniedByDefault() {
    CallbackOpsAuthorizationPort deny = (op, actor) -> Mono.just(AuthorizationDecision.DENY);
    CallbackOutboxProcessor outboxProcessor =
        new CallbackOutboxProcessor(
            new InMemoryCallbackOutboxStore(),
            new br.com.banco.spider.infrastructure.persistence.memory
                .InMemoryCallbackDeliveryAttemptStore(),
            new br.com.banco.spider.infrastructure.persistence.memory
                .InMemoryExecutionCallbackContextStore(),
            null,
            new br.com.banco.spider.execution.callback.ConfiguredCallbackDeliveryPolicyCatalog(
                java.util.List.of()),
            new br.com.banco.spider.execution.callback.ConfiguredCallbackDefinitionCatalog(
                java.util.List.of()),
            null,
            new br.com.banco.spider.execution.callback.DenyAllCallbackAuthorizationAdapter(),
            new br.com.banco.spider.execution.callback.ConfiguredCallbackBindingResolver(
                java.util.Map.of()),
            IdentifierGenerator.fixed(() -> "1"),
            SpiderClock.fixed(Instant.parse("2026-08-21T12:00:00Z")));
    CallbackProcessingRecoveryService recovery =
        new CallbackProcessingRecoveryService(
            new InMemoryCallbackOutboxStore(),
            new InMemoryCallbackReconciliationStore(),
            outboxProcessor,
            SpiderClock.fixed(Instant.parse("2026-08-21T12:00:00Z")));
    RecoverCallbackProcessingUseCase useCase =
        new RecoverCallbackProcessingUseCase(
            deny, recovery, SpiderClock.fixed(Instant.parse("2026-08-21T12:00:00Z")));
    StepVerifier.create(useCase.execute(new RecoverCallbackProcessingUseCase.Command("a", "R")))
        .assertNext(
            o -> {
              assertEquals(AuthorizationDecision.DENY, o.decision());
              assertNull(o.summary());
            })
        .verifyComplete();
  }
}
