package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.execution.callback.CallbackDeliveryStatusDisposition;
import br.com.banco.spider.execution.callback.CallbackReconciliationRecord;
import br.com.banco.spider.execution.callback.CallbackReconciliationState;
import br.com.banco.spider.execution.persistence.port.CallbackReconciliationStorePort;
import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryCallbackReconciliationStore implements CallbackReconciliationStorePort {

  private final Map<String, CallbackReconciliationRecord> byId = new ConcurrentHashMap<>();
  private final Map<String, String> byOutbox = new ConcurrentHashMap<>();
  private final Map<String, String> byExecution = new ConcurrentHashMap<>();

  @Override
  public synchronized CallbackReconciliationRecord insertIdempotent(
      CallbackReconciliationRecord record) {
    String existing = byOutbox.get(record.outboxId());
    if (existing != null) {
      return byId.get(existing);
    }
    byId.put(record.reconciliationId(), record);
    byOutbox.put(record.outboxId(), record.reconciliationId());
    byExecution.put(record.executionId(), record.reconciliationId());
    return record;
  }

  @Override
  public Optional<CallbackReconciliationRecord> findByReconciliationId(String reconciliationId) {
    return Optional.ofNullable(byId.get(reconciliationId));
  }

  @Override
  public Optional<CallbackReconciliationRecord> findByOutboxId(String outboxId) {
    String id = byOutbox.get(outboxId);
    return id == null ? Optional.empty() : Optional.ofNullable(byId.get(id));
  }

  @Override
  public Optional<CallbackReconciliationRecord> findByExecutionId(String executionId) {
    String id = byExecution.get(executionId);
    return id == null ? Optional.empty() : Optional.ofNullable(byId.get(id));
  }

  @Override
  public List<CallbackReconciliationRecord> findDue(Instant now, int limit) {
    return byId.values().stream()
        .filter(
            r ->
                (r.state() == CallbackReconciliationState.PENDING
                        || r.state() == CallbackReconciliationState.RETRY_SCHEDULED)
                    && !r.nextQueryAt().isAfter(now)
                    && r.expiresAt().isAfter(now)
                    && (r.leaseUntil() == null || r.leaseUntil().isBefore(now)))
        .sorted(
            Comparator.comparing(CallbackReconciliationRecord::nextQueryAt)
                .thenComparing(CallbackReconciliationRecord::reconciliationId))
        .limit(limit)
        .toList();
  }

  @Override
  public synchronized Optional<CallbackReconciliationRecord> claim(
      String reconciliationId,
      long expectedVersion,
      String workerId,
      Instant leaseUntil,
      Instant now) {
    CallbackReconciliationRecord current = byId.get(reconciliationId);
    if (current == null || current.version() != expectedVersion) {
      return Optional.empty();
    }
    if (current.leaseUntil() != null
        && current.leaseUntil().isAfter(now)
        && current.leaseOwner() != null
        && !current.leaseOwner().equals(workerId)) {
      return Optional.empty();
    }
    if (current.state() != CallbackReconciliationState.PENDING
        && current.state() != CallbackReconciliationState.RETRY_SCHEDULED) {
      return Optional.empty();
    }
    CallbackReconciliationRecord updated =
        copy(
            current,
            CallbackReconciliationState.QUERYING,
            current.queryCount(),
            current.nextQueryAt(),
            current.lastDisposition(),
            current.externalDeliveryRef(),
            workerId,
            leaseUntil,
            now);
    byId.put(reconciliationId, updated);
    return Optional.of(updated);
  }

  @Override
  public synchronized CallbackReconciliationRecord update(
      String reconciliationId,
      long expectedVersion,
      CallbackReconciliationState state,
      int queryCount,
      Instant nextQueryAt,
      CallbackDeliveryStatusDisposition lastDisposition,
      String externalDeliveryRef,
      String leaseOwner,
      Instant leaseUntil,
      Instant now) {
    CallbackReconciliationRecord current = byId.get(reconciliationId);
    if (current == null || current.version() != expectedVersion) {
      throw new InMemoryExecutionControlStore.OptimisticLockException("Reconciliation version");
    }
    CallbackReconciliationRecord updated =
        copy(
            current,
            state,
            queryCount,
            nextQueryAt != null ? nextQueryAt : current.nextQueryAt(),
            lastDisposition != null ? lastDisposition : current.lastDisposition(),
            externalDeliveryRef != null ? externalDeliveryRef : current.externalDeliveryRef(),
            leaseOwner,
            leaseUntil,
            now);
    byId.put(reconciliationId, updated);
    return updated;
  }

  @Override
  public List<CallbackReconciliationRecord> findExpiredLeases(Instant now) {
    return byId.values().stream()
        .filter(
            r ->
                r.state() == CallbackReconciliationState.QUERYING
                    && r.leaseUntil() != null
                    && !r.leaseUntil().isAfter(now))
        .toList();
  }

  private static CallbackReconciliationRecord copy(
      CallbackReconciliationRecord current,
      CallbackReconciliationState state,
      int queryCount,
      Instant nextQueryAt,
      CallbackDeliveryStatusDisposition lastDisposition,
      String externalDeliveryRef,
      String leaseOwner,
      Instant leaseUntil,
      Instant now) {
    return new CallbackReconciliationRecord(
        current.reconciliationId(),
        current.outboxId(),
        current.executionId(),
        current.deliveryKeyHash(),
        current.policyRef(),
        state,
        queryCount,
        nextQueryAt,
        current.startedAt(),
        current.expiresAt(),
        lastDisposition,
        externalDeliveryRef,
        leaseOwner,
        leaseUntil,
        current.version() + 1,
        current.createdAt(),
        now);
  }

  public void clear() {
    byId.clear();
    byOutbox.clear();
    byExecution.clear();
  }
}
