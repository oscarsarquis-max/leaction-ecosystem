package br.com.banco.spider.operational.workers;

import br.com.banco.spider.execution.callback.CallbackReconciliationRecord;
import br.com.banco.spider.execution.inbox.InboxProcessingState;
import br.com.banco.spider.execution.inbox.InboxRecord;
import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import br.com.banco.spider.execution.persistence.port.CallbackReconciliationStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.persistence.port.InboxStorePort;
import br.com.banco.spider.execution.signal.protection.ProtectedEnvelopeState;
import br.com.banco.spider.execution.signal.protection.ProtectedSignalEnvelope;
import br.com.banco.spider.execution.signal.protection.ProtectedSignalEnvelopeStorePort;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import org.springframework.beans.factory.ObjectProvider;

/**
 * Backlog por tipo de worker, sempre lido das fontes canônicas reais.
 *
 * <p>As portas existentes expõem consultas limitadas, não contagens. O serviço usa essas consultas
 * com teto de {@value #MAX_SCAN} itens: quando o teto é atingido a contagem é declarada aproximada,
 * em vez de forçar uma varredura ilimitada só para produzir um número exato.
 */
public class WorkerBacklogQueryService {

  public static final int MAX_SCAN = 500;
  private static final Duration STALE_THRESHOLD = Duration.ofMinutes(5);

  private final WorkerRuntimeCatalog catalog;
  private final SpiderClock clock;
  private final ObjectProvider<InboxStorePort> inboxProvider;
  private final ObjectProvider<ExecutionWaitStorePort> waitProvider;
  private final ObjectProvider<CallbackOutboxStorePort> outboxProvider;
  private final ObjectProvider<CallbackReconciliationStorePort> reconciliationProvider;
  private final ObjectProvider<ProtectedSignalEnvelopeStorePort> protectedProvider;

  public WorkerBacklogQueryService(
      WorkerRuntimeCatalog catalog,
      SpiderClock clock,
      ObjectProvider<InboxStorePort> inboxProvider,
      ObjectProvider<ExecutionWaitStorePort> waitProvider,
      ObjectProvider<CallbackOutboxStorePort> outboxProvider,
      ObjectProvider<CallbackReconciliationStorePort> reconciliationProvider,
      ObjectProvider<ProtectedSignalEnvelopeStorePort> protectedProvider) {
    this.catalog = catalog;
    this.clock = clock;
    this.inboxProvider = inboxProvider;
    this.waitProvider = waitProvider;
    this.outboxProvider = outboxProvider;
    this.reconciliationProvider = reconciliationProvider;
    this.protectedProvider = protectedProvider;
  }

  public List<WorkerBacklogView> backlogs() {
    Instant now = clock.now();
    List<WorkerBacklogView> views = new ArrayList<>();
    for (WorkerTypeDefinition definition : catalog.definitions()) {
      views.add(backlog(definition, now));
    }
    return List.copyOf(views);
  }

  public WorkerBacklogView backlog(WorkerType workerType) {
    return backlog(catalog.definition(workerType), clock.now());
  }

  private WorkerBacklogView backlog(WorkerTypeDefinition definition, Instant now) {
    return switch (definition.workerType()) {
      case SIGNAL_APPLICATION -> signalApplication(definition, now);
      case WAIT_EXPIRY -> waitExpiry(definition, now);
      case CALLBACK_DELIVERY -> callbackDelivery(definition, now);
      case CALLBACK_RECONCILIATION -> callbackReconciliation(definition, now);
      case CALLBACK_RECOVERY -> callbackRecovery(definition, now);
      case SIGNAL_APPLICATION_RECOVERY -> signalApplicationRecovery(definition, now);
      case PROTECTED_ENVELOPE_MAINTENANCE -> protectedEnvelope(definition, now);
    };
  }

  private WorkerBacklogView signalApplication(WorkerTypeDefinition definition, Instant now) {
    InboxStorePort store = inboxProvider.getIfAvailable();
    if (store == null) {
      return WorkerBacklogView.unknown(definition.workerType(), "inboxStore indisponível");
    }
    List<InboxRecord> due = store.findDueForApplication(now, MAX_SCAN);
    Instant oldest =
        due.stream()
            .map(record -> record.nextAttemptAt() == null ? record.receivedAt() : record.nextAttemptAt())
            .filter(java.util.Objects::nonNull)
            .min(Instant::compareTo)
            .orElse(null);
    return view(definition, now, due.size(), oldest, "inbox aguardando aplicação de sinal");
  }

  private WorkerBacklogView waitExpiry(WorkerTypeDefinition definition, Instant now) {
    ExecutionWaitStorePort store = waitProvider.getIfAvailable();
    if (store == null) {
      return WorkerBacklogView.unknown(definition.workerType(), "executionWaitStore indisponível");
    }
    List<ExecutionWaitRecord> expired =
        store.findExpiredWaiting(now).stream().limit(MAX_SCAN).toList();
    Instant oldest =
        expired.stream()
            .map(ExecutionWaitRecord::expiresAt)
            .filter(java.util.Objects::nonNull)
            .min(Instant::compareTo)
            .orElse(null);
    return view(definition, now, expired.size(), oldest, "esperas vencidas aguardando expiração");
  }

  private WorkerBacklogView callbackDelivery(WorkerTypeDefinition definition, Instant now) {
    CallbackOutboxStorePort store = outboxProvider.getIfAvailable();
    if (store == null) {
      return WorkerBacklogView.unknown(definition.workerType(), "callbackOutboxStore indisponível");
    }
    var ready = store.findReady(now, MAX_SCAN);
    Instant oldest =
        ready.stream()
            .map(record -> record.nextAttemptAt())
            .filter(java.util.Objects::nonNull)
            .min(Instant::compareTo)
            .orElse(null);
    return view(definition, now, ready.size(), oldest, "callbacks prontos para despacho");
  }

  private WorkerBacklogView callbackReconciliation(WorkerTypeDefinition definition, Instant now) {
    CallbackReconciliationStorePort store = reconciliationProvider.getIfAvailable();
    if (store == null) {
      return WorkerBacklogView.unknown(
          definition.workerType(), "callbackReconciliationStore indisponível");
    }
    List<CallbackReconciliationRecord> due = store.findDue(now, MAX_SCAN);
    Instant oldest =
        due.stream()
            .map(CallbackReconciliationRecord::nextQueryAt)
            .filter(java.util.Objects::nonNull)
            .min(Instant::compareTo)
            .orElse(null);
    return view(definition, now, due.size(), oldest, "reconciliações devidas");
  }

  private WorkerBacklogView callbackRecovery(WorkerTypeDefinition definition, Instant now) {
    CallbackReconciliationStorePort reconciliations = reconciliationProvider.getIfAvailable();
    CallbackOutboxStorePort outbox = outboxProvider.getIfAvailable();
    if (reconciliations == null && outbox == null) {
      return WorkerBacklogView.unknown(definition.workerType(), "fontes de recuperação indisponíveis");
    }
    int count = 0;
    Instant oldest = null;
    if (reconciliations != null) {
      List<CallbackReconciliationRecord> leases =
          reconciliations.findExpiredLeases(now).stream().limit(MAX_SCAN).toList();
      count += leases.size();
      oldest =
          leases.stream()
              .map(CallbackReconciliationRecord::leaseUntil)
              .filter(java.util.Objects::nonNull)
              .min(Instant::compareTo)
              .orElse(null);
    }
    if (outbox != null) {
      var interrupted = outbox.findInterruptedDispatching(now).stream().limit(MAX_SCAN).toList();
      count += interrupted.size();
    }
    return view(definition, now, count, oldest, "leases de callback vencidos");
  }

  private WorkerBacklogView signalApplicationRecovery(
      WorkerTypeDefinition definition, Instant now) {
    InboxStorePort store = inboxProvider.getIfAvailable();
    if (store == null) {
      return WorkerBacklogView.unknown(definition.workerType(), "inboxStore indisponível");
    }
    List<InboxRecord> interrupted =
        store.findByProcessingState(InboxProcessingState.APPLYING).stream()
            .filter(record -> record.leaseUntil() == null || !record.leaseUntil().isAfter(now))
            .limit(MAX_SCAN)
            .toList();
    Instant oldest =
        interrupted.stream()
            .map(InboxRecord::leaseUntil)
            .filter(java.util.Objects::nonNull)
            .min(Instant::compareTo)
            .orElse(null);
    return view(definition, now, interrupted.size(), oldest, "leases de aplicação vencidos");
  }

  private WorkerBacklogView protectedEnvelope(WorkerTypeDefinition definition, Instant now) {
    ProtectedSignalEnvelopeStorePort store = protectedProvider.getIfAvailable();
    if (store == null) {
      return WorkerBacklogView.unknown(
          definition.workerType(), "protectedSignalEnvelopeStore indisponível");
    }
    List<ProtectedSignalEnvelope> eligible =
        store.findByState(ProtectedEnvelopeState.DELETION_ELIGIBLE).stream()
            .limit(MAX_SCAN)
            .toList();
    Instant oldest =
        eligible.stream()
            .map(ProtectedSignalEnvelope::consumedAt)
            .filter(java.util.Objects::nonNull)
            .min(Instant::compareTo)
            .orElse(null);
    return view(definition, now, eligible.size(), oldest, "envelopes elegíveis a retenção");
  }

  private WorkerBacklogView view(
      WorkerTypeDefinition definition,
      Instant now,
      int count,
      Instant oldest,
      String explanation) {
    boolean approximate = count >= MAX_SCAN;
    Long oldestAgeMs =
        oldest == null ? null : Math.max(0L, Duration.between(oldest, now).toMillis());
    WorkerBacklogStatus status;
    if (count == 0) {
      status = WorkerBacklogStatus.EMPTY;
    } else if (oldestAgeMs != null && oldestAgeMs > STALE_THRESHOLD.toMillis()) {
      status = WorkerBacklogStatus.STALE;
    } else if (count >= definition.batchSize()) {
      status = WorkerBacklogStatus.ACCUMULATING;
    } else {
      status = WorkerBacklogStatus.NORMAL;
    }
    return new WorkerBacklogView(
        WorkerBacklogView.SCHEMA_VERSION,
        definition.workerType(),
        status,
        count,
        oldestAgeMs,
        approximate,
        explanation);
  }
}
