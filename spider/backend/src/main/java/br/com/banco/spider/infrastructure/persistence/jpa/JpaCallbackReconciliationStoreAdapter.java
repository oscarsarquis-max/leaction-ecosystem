package br.com.banco.spider.infrastructure.persistence.jpa;

import br.com.banco.spider.execution.callback.CallbackDeliveryStatusDisposition;
import br.com.banco.spider.execution.callback.CallbackReconciliationRecord;
import br.com.banco.spider.execution.callback.CallbackReconciliationState;
import br.com.banco.spider.execution.persistence.port.CallbackReconciliationStorePort;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.CallbackReconciliationEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.CallbackReconciliationJpaRepository;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
public class JpaCallbackReconciliationStoreAdapter implements CallbackReconciliationStorePort {

  private final CallbackReconciliationJpaRepository repo;

  public JpaCallbackReconciliationStoreAdapter(CallbackReconciliationJpaRepository repo) {
    this.repo = repo;
  }

  @Override
  @Transactional
  public CallbackReconciliationRecord insertIdempotent(CallbackReconciliationRecord record) {
    Optional<CallbackReconciliationEntity> existing = repo.findByOutboxId(record.outboxId());
    if (existing.isPresent()) {
      return toModel(existing.get());
    }
    try {
      return toModel(repo.save(toEntity(record)));
    } catch (DataIntegrityViolationException ex) {
      return repo.findByOutboxId(record.outboxId()).map(this::toModel).orElseThrow(() -> ex);
    }
  }

  @Override
  public Optional<CallbackReconciliationRecord> findByReconciliationId(String reconciliationId) {
    return repo.findById(reconciliationId).map(this::toModel);
  }

  @Override
  public Optional<CallbackReconciliationRecord> findByOutboxId(String outboxId) {
    return repo.findByOutboxId(outboxId).map(this::toModel);
  }

  @Override
  public Optional<CallbackReconciliationRecord> findByExecutionId(String executionId) {
    return repo.findByExecutionId(executionId).map(this::toModel);
  }

  @Override
  public List<CallbackReconciliationRecord> findDue(Instant now, int limit) {
    return repo.findDue(
            List.of(
                CallbackReconciliationState.PENDING, CallbackReconciliationState.RETRY_SCHEDULED),
            now)
        .stream()
        .limit(limit)
        .map(this::toModel)
        .toList();
  }

  @Override
  @Transactional
  public Optional<CallbackReconciliationRecord> claim(
      String reconciliationId,
      long expectedVersion,
      String workerId,
      Instant leaseUntil,
      Instant now) {
    Optional<CallbackReconciliationEntity> opt = repo.findById(reconciliationId);
    if (opt.isEmpty()) {
      return Optional.empty();
    }
    CallbackReconciliationEntity e = opt.get();
    if (e.getVersion() != expectedVersion) {
      return Optional.empty();
    }
    if (e.getLeaseUntil() != null
        && e.getLeaseUntil().isAfter(now)
        && e.getLeaseOwner() != null
        && !e.getLeaseOwner().equals(workerId)) {
      return Optional.empty();
    }
    if (e.getState() != CallbackReconciliationState.PENDING
        && e.getState() != CallbackReconciliationState.RETRY_SCHEDULED) {
      return Optional.empty();
    }
    e.setState(CallbackReconciliationState.QUERYING);
    e.setLeaseOwner(workerId);
    e.setLeaseUntil(leaseUntil);
    e.setUpdatedAt(now);
    return Optional.of(toModel(repo.save(e)));
  }

  @Override
  @Transactional
  public CallbackReconciliationRecord update(
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
    CallbackReconciliationEntity e =
        repo.findById(reconciliationId)
            .orElseThrow(() -> new IllegalStateException("Reconciliation not found"));
    if (e.getVersion() != expectedVersion) {
      throw new IllegalStateException("Optimistic lock conflict");
    }
    e.setState(state);
    e.setQueryCount(queryCount);
    if (nextQueryAt != null) {
      e.setNextQueryAt(nextQueryAt);
    }
    if (lastDisposition != null) {
      e.setLastDisposition(lastDisposition);
    }
    if (externalDeliveryRef != null) {
      e.setExternalDeliveryRef(externalDeliveryRef);
    }
    e.setLeaseOwner(leaseOwner);
    e.setLeaseUntil(leaseUntil);
    e.setUpdatedAt(now);
    return toModel(repo.save(e));
  }

  @Override
  public List<CallbackReconciliationRecord> findExpiredLeases(Instant now) {
    return repo
        .findByStateAndLeaseUntilLessThanEqual(CallbackReconciliationState.QUERYING, now)
        .stream()
        .map(this::toModel)
        .toList();
  }

  private CallbackReconciliationEntity toEntity(CallbackReconciliationRecord r) {
    CallbackReconciliationEntity e = new CallbackReconciliationEntity();
    e.setReconciliationId(r.reconciliationId());
    e.setOutboxId(r.outboxId());
    e.setExecutionId(r.executionId());
    e.setDeliveryKeyHash(r.deliveryKeyHash());
    e.setPolicyRef(r.policyRef());
    e.setState(r.state());
    e.setQueryCount(r.queryCount());
    e.setNextQueryAt(r.nextQueryAt());
    e.setStartedAt(r.startedAt());
    e.setExpiresAt(r.expiresAt());
    e.setLastDisposition(r.lastDisposition());
    e.setExternalDeliveryRef(r.externalDeliveryRef());
    e.setLeaseOwner(r.leaseOwner());
    e.setLeaseUntil(r.leaseUntil());
    e.setVersion(r.version());
    e.setCreatedAt(r.createdAt());
    e.setUpdatedAt(r.updatedAt());
    return e;
  }

  private CallbackReconciliationRecord toModel(CallbackReconciliationEntity e) {
    return new CallbackReconciliationRecord(
        e.getReconciliationId(),
        e.getOutboxId(),
        e.getExecutionId(),
        e.getDeliveryKeyHash(),
        e.getPolicyRef(),
        e.getState(),
        e.getQueryCount(),
        e.getNextQueryAt(),
        e.getStartedAt(),
        e.getExpiresAt(),
        e.getLastDisposition(),
        e.getExternalDeliveryRef(),
        e.getLeaseOwner(),
        e.getLeaseUntil(),
        e.getVersion(),
        e.getCreatedAt(),
        e.getUpdatedAt());
  }
}
