package br.com.banco.spider.execution.persistence.support;

import br.com.banco.spider.execution.fingerprint.Sha256CanonicalRequestFingerprint;
import br.com.banco.spider.execution.fingerprint.Sha256IdempotencyKeyHash;
import br.com.banco.spider.execution.persistence.CanonicalExecutionResultSerializer;
import br.com.banco.spider.execution.persistence.ExecutionPersistenceCoordinator;
import br.com.banco.spider.execution.persistence.ReactiveExecutionPersistenceGateway;
import br.com.banco.spider.execution.retry.BackoffStrategyPort;
import br.com.banco.spider.execution.retry.ControlledRetryExecutor;
import br.com.banco.spider.execution.retry.ExponentialCappedBackoff;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.IntegrityDigestPort;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.execution.wait.ConfiguredWaitPolicyCatalog;
import br.com.banco.spider.execution.wait.WaitCreationService;
import br.com.banco.spider.execution.wait.WaitPolicyDefinition;
import br.com.banco.spider.infrastructure.persistence.BlockingPersistenceSupport;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionControlStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionPlanStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionResultStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionStepStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionTransitionStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionWaitStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryIdempotencyStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryInboxStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryStepAttemptStore;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import java.time.Duration;
import java.util.List;
import reactor.core.scheduler.Schedulers;

/** Montagem rápida de persistência em memória para testes. */
public final class InMemoryPersistenceBundle {

  public final InMemoryExecutionControlStore controlStore = new InMemoryExecutionControlStore();
  public final InMemoryExecutionPlanStore planStore = new InMemoryExecutionPlanStore();
  public final InMemoryExecutionTransitionStore transitionStore = new InMemoryExecutionTransitionStore();
  public final InMemoryExecutionResultStore resultStore = new InMemoryExecutionResultStore();
  public final InMemoryIdempotencyStore idempotencyStore = new InMemoryIdempotencyStore();
  public final InMemoryExecutionStepStore stepStore = new InMemoryExecutionStepStore();
  public final InMemoryStepAttemptStore attemptStore = new InMemoryStepAttemptStore();
  public final InMemoryExecutionWaitStore waitStore = new InMemoryExecutionWaitStore();
  public final InMemoryInboxStore inboxStore = new InMemoryInboxStore();
  public final ExecutionPersistenceCoordinator coordinator;
  public final ReactiveExecutionPersistenceGateway gateway;
  public final ControlledRetryExecutor retryExecutor;
  public final WaitCreationService waitCreation;
  public final ConfiguredWaitPolicyCatalog waitPolicies;
  public final Sha256IdempotencyKeyHash keyHash = new Sha256IdempotencyKeyHash();
  public final Sha256CanonicalRequestFingerprint fingerprint;
  public final BackoffStrategyPort backoff = new ExponentialCappedBackoff();

  public InMemoryPersistenceBundle(SpiderClock clock, IdentifierGenerator ids) {
    ObjectMapper mapper = new ObjectMapper().registerModule(new JavaTimeModule());
    this.fingerprint = new Sha256CanonicalRequestFingerprint(mapper);
    CanonicalExecutionResultSerializer serializer =
        new CanonicalExecutionResultSerializer(mapper, IntegrityDigestPort.sha256(), 65536);
    this.coordinator =
        new ExecutionPersistenceCoordinator(
            controlStore,
            planStore,
            transitionStore,
            resultStore,
            idempotencyStore,
            stepStore,
            fingerprint,
            keyHash,
            serializer,
            ids,
            clock,
            Duration.ofHours(24),
            Duration.ofHours(24));
    this.gateway =
        new ReactiveExecutionPersistenceGateway(
            coordinator, new BlockingPersistenceSupport(Schedulers.immediate()));
    this.retryExecutor =
        new ControlledRetryExecutor(stepStore, attemptStore, backoff, ids, clock);
    this.waitPolicies =
        new ConfiguredWaitPolicyCatalog(
            List.of(
                WaitPolicyDefinition.publishedAsync(
                    "default-async",
                    "1.0",
                    Duration.ofMinutes(5),
                    List.of("source:mock-async@1.0", "source:test-signal@1.0")),
                WaitPolicyDefinition.publishedUnknown(
                    "default-unknown",
                    "1.0",
                    Duration.ofMinutes(5),
                    List.of("source:mock-async@1.0", "source:test-signal@1.0"))));
    this.waitCreation = new WaitCreationService(waitStore, waitPolicies, ids, clock);
  }

  public void clear() {
    controlStore.clear();
    planStore.clear();
    transitionStore.clear();
    resultStore.clear();
    idempotencyStore.clear();
    stepStore.clear();
    attemptStore.clear();
    waitStore.clear();
    inboxStore.clear();
  }
}
