package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.execution.callback.CallbackOutboxRecord;
import br.com.banco.spider.execution.callback.CallbackOutboxState;
import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryCallbackOutboxStore implements CallbackOutboxStorePort {

  private final Map<String, CallbackOutboxRecord> byId = new ConcurrentHashMap<>();
  private final Map<String, String> logicalToId = new ConcurrentHashMap<>();
  private final Map<String, String> executionToId = new ConcurrentHashMap<>();

  @Override
  public synchronized CallbackOutboxRecord insertIdempotent(CallbackOutboxRecord record) {
    String existingId = logicalToId.get(record.logicalCallbackId());
    if (existingId != null) {
      return byId.get(existingId);
    }
    String execExisting = executionToId.get(record.executionId());
    if (execExisting != null) {
      return byId.get(execExisting);
    }
    byId.put(record.outboxId(), record);
    logicalToId.put(record.logicalCallbackId(), record.outboxId());
    executionToId.put(record.executionId(), record.outboxId());
    return record;
  }

  @Override
  public Optional<CallbackOutboxRecord> findByOutboxId(String outboxId) {
    return Optional.ofNullable(byId.get(outboxId));
  }

  @Override
  public Optional<CallbackOutboxRecord> findByLogicalCallbackId(String logicalCallbackId) {
    String id = logicalToId.get(logicalCallbackId);
    return id == null ? Optional.empty() : Optional.ofNullable(byId.get(id));
  }

  @Override
  public Optional<CallbackOutboxRecord> findByExecutionId(String executionId) {
    String id = executionToId.get(executionId);
    return id == null ? Optional.empty() : Optional.ofNullable(byId.get(id));
  }

  @Override
  public synchronized CallbackOutboxRecord claim(
      String outboxId,
      CallbackOutboxState expectedState,
      long expectedVersion,
      CallbackOutboxState newState,
      Instant now) {
    CallbackOutboxRecord current = byId.get(outboxId);
    if (current == null) {
      throw new IllegalStateException("Outbox not found");
    }
    if (current.state() != expectedState || current.stateVersion() != expectedVersion) {
      throw new InMemoryExecutionControlStore.OptimisticLockException("Outbox claim conflict");
    }
    CallbackOutboxRecord updated =
        new CallbackOutboxRecord(
            current.outboxId(),
            current.logicalCallbackId(),
            current.executionId(),
            current.callbackDefinitionRef(),
            current.bindingRef(),
            current.contractRef(),
            current.securityProfileRef(),
            current.projectionRef(),
            current.resultRef(),
            current.logicalIdempotencyKeyHash(),
            newState,
            current.createdAt(),
            current.nextAttemptAt(),
            current.expiresAt(),
            current.attemptCount(),
            current.stateVersion() + 1,
            current.lastErrorCode());
    byId.put(outboxId, updated);
    return updated;
  }

  @Override
  public List<CallbackOutboxRecord> findReady(Instant now, int limit) {
    return byId.values().stream()
        .filter(
            r ->
                (r.state() == CallbackOutboxState.PENDING
                        || r.state() == CallbackOutboxState.RETRY_SCHEDULED)
                    && !r.nextAttemptAt().isAfter(now)
                    && r.expiresAt().isAfter(now))
        .sorted(Comparator.comparing(CallbackOutboxRecord::nextAttemptAt))
        .limit(limit)
        .toList();
  }

  @Override
  public List<CallbackOutboxRecord> findInterruptedDispatching(Instant leaseExpiredBefore) {
    List<CallbackOutboxRecord> list = new ArrayList<>();
    for (CallbackOutboxRecord r : byId.values()) {
      if (r.state() == CallbackOutboxState.DISPATCHING
          && r.nextAttemptAt().isBefore(leaseExpiredBefore)) {
        list.add(r);
      }
    }
    return list;
  }

  @Override
  public synchronized CallbackOutboxRecord updateState(
      String outboxId,
      long expectedVersion,
      CallbackOutboxState newState,
      Instant nextAttemptAt,
      int attemptCount,
      String lastErrorCode,
      Instant now) {
    CallbackOutboxRecord current = byId.get(outboxId);
    if (current == null) {
      throw new IllegalStateException("Outbox not found");
    }
    if (current.stateVersion() != expectedVersion) {
      throw new InMemoryExecutionControlStore.OptimisticLockException("Outbox version mismatch");
    }
    CallbackOutboxRecord updated =
        new CallbackOutboxRecord(
            current.outboxId(),
            current.logicalCallbackId(),
            current.executionId(),
            current.callbackDefinitionRef(),
            current.bindingRef(),
            current.contractRef(),
            current.securityProfileRef(),
            current.projectionRef(),
            current.resultRef(),
            current.logicalIdempotencyKeyHash(),
            newState,
            current.createdAt(),
            nextAttemptAt != null ? nextAttemptAt : current.nextAttemptAt(),
            current.expiresAt(),
            attemptCount,
            current.stateVersion() + 1,
            lastErrorCode != null ? lastErrorCode : current.lastErrorCode());
    byId.put(outboxId, updated);
    return updated;
  }

  public void clear() {
    byId.clear();
    logicalToId.clear();
    executionToId.clear();
  }
}
