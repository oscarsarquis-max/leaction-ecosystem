package br.com.banco.spider.infrastructure.persistence.jpa;

import br.com.banco.spider.execution.callback.CallbackOutboxRecord;
import br.com.banco.spider.execution.callback.CallbackOutboxState;
import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.CallbackOutboxEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.CallbackOutboxJpaRepository;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionControlStore;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
public class JpaCallbackOutboxStoreAdapter implements CallbackOutboxStorePort {

  private final CallbackOutboxJpaRepository repo;

  public JpaCallbackOutboxStoreAdapter(CallbackOutboxJpaRepository repo) {
    this.repo = repo;
  }

  @Override
  @Transactional
  public CallbackOutboxRecord insertIdempotent(CallbackOutboxRecord record) {
    Optional<CallbackOutboxEntity> existing =
        repo.findByLogicalCallbackId(record.logicalCallbackId());
    if (existing.isPresent()) {
      return toModel(existing.get());
    }
    existing = repo.findByExecutionId(record.executionId());
    if (existing.isPresent()) {
      return toModel(existing.get());
    }
    try {
      return toModel(repo.save(toEntity(record)));
    } catch (DataIntegrityViolationException ex) {
      return repo.findByLogicalCallbackId(record.logicalCallbackId())
          .map(this::toModel)
          .orElseThrow(() -> new IllegalStateException("Outbox race", ex));
    }
  }

  @Override
  public Optional<CallbackOutboxRecord> findByOutboxId(String outboxId) {
    return repo.findById(outboxId).map(this::toModel);
  }

  @Override
  public Optional<CallbackOutboxRecord> findByLogicalCallbackId(String logicalCallbackId) {
    return repo.findByLogicalCallbackId(logicalCallbackId).map(this::toModel);
  }

  @Override
  public Optional<CallbackOutboxRecord> findByExecutionId(String executionId) {
    return repo.findByExecutionId(executionId).map(this::toModel);
  }

  @Override
  @Transactional
  public CallbackOutboxRecord claim(
      String outboxId,
      CallbackOutboxState expectedState,
      long expectedVersion,
      CallbackOutboxState newState,
      Instant now) {
    CallbackOutboxEntity e =
        repo.findById(outboxId).orElseThrow(() -> new IllegalStateException("Outbox not found"));
    if (e.getState() != expectedState || e.getStateVersion() != expectedVersion) {
      throw new InMemoryExecutionControlStore.OptimisticLockException("Outbox claim conflict");
    }
    e.setState(newState);
    e.setStateVersion(e.getStateVersion() + 1);
    return toModel(repo.save(e));
  }

  @Override
  public List<CallbackOutboxRecord> findReady(Instant now, int limit) {
    return repo
        .findReady(
            List.of(CallbackOutboxState.PENDING, CallbackOutboxState.RETRY_SCHEDULED), now)
        .stream()
        .limit(limit)
        .map(this::toModel)
        .toList();
  }

  @Override
  public List<CallbackOutboxRecord> findInterruptedDispatching(Instant leaseExpiredBefore) {
    return repo
        .findByStateAndNextAttemptAtBefore(CallbackOutboxState.DISPATCHING, leaseExpiredBefore)
        .stream()
        .map(this::toModel)
        .toList();
  }

  @Override
  @Transactional
  public CallbackOutboxRecord updateState(
      String outboxId,
      long expectedVersion,
      CallbackOutboxState newState,
      Instant nextAttemptAt,
      int attemptCount,
      String lastErrorCode,
      Instant now) {
    CallbackOutboxEntity e =
        repo.findById(outboxId).orElseThrow(() -> new IllegalStateException("Outbox not found"));
    if (e.getStateVersion() != expectedVersion) {
      throw new InMemoryExecutionControlStore.OptimisticLockException("Outbox version mismatch");
    }
    e.setState(newState);
    e.setStateVersion(e.getStateVersion() + 1);
    e.setAttemptCount(attemptCount);
    if (nextAttemptAt != null) {
      e.setNextAttemptAt(nextAttemptAt);
    }
    if (lastErrorCode != null) {
      e.setLastErrorCode(lastErrorCode);
    }
    return toModel(repo.save(e));
  }

  private CallbackOutboxEntity toEntity(CallbackOutboxRecord r) {
    CallbackOutboxEntity e = new CallbackOutboxEntity();
    e.setOutboxId(r.outboxId());
    e.setLogicalCallbackId(r.logicalCallbackId());
    e.setExecutionId(r.executionId());
    e.setCallbackDefinitionRef(r.callbackDefinitionRef());
    e.setBindingRef(r.bindingRef());
    e.setContractRef(r.contractRef());
    e.setSecurityProfileRef(r.securityProfileRef());
    e.setProjectionRef(r.projectionRef());
    e.setResultRef(r.resultRef());
    e.setLogicalIdempotencyKeyHash(r.logicalIdempotencyKeyHash());
    e.setState(r.state());
    e.setCreatedAt(r.createdAt());
    e.setNextAttemptAt(r.nextAttemptAt());
    e.setExpiresAt(r.expiresAt());
    e.setAttemptCount(r.attemptCount());
    e.setStateVersion(r.stateVersion());
    e.setLastErrorCode(r.lastErrorCode());
    return e;
  }

  private CallbackOutboxRecord toModel(CallbackOutboxEntity e) {
    return new CallbackOutboxRecord(
        e.getOutboxId(),
        e.getLogicalCallbackId(),
        e.getExecutionId(),
        e.getCallbackDefinitionRef(),
        e.getBindingRef(),
        e.getContractRef(),
        e.getSecurityProfileRef(),
        e.getProjectionRef(),
        e.getResultRef(),
        e.getLogicalIdempotencyKeyHash(),
        e.getState(),
        e.getCreatedAt(),
        e.getNextAttemptAt(),
        e.getExpiresAt(),
        e.getAttemptCount(),
        e.getStateVersion(),
        e.getLastErrorCode());
  }
}
