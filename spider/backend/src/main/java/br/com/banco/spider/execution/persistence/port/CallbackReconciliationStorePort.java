package br.com.banco.spider.execution.persistence.port;

import br.com.banco.spider.execution.callback.CallbackDeliveryStatusDisposition;
import br.com.banco.spider.execution.callback.CallbackReconciliationRecord;
import br.com.banco.spider.execution.callback.CallbackReconciliationState;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

public interface CallbackReconciliationStorePort {

  CallbackReconciliationRecord insertIdempotent(CallbackReconciliationRecord record);

  Optional<CallbackReconciliationRecord> findByReconciliationId(String reconciliationId);

  Optional<CallbackReconciliationRecord> findByOutboxId(String outboxId);

  Optional<CallbackReconciliationRecord> findByExecutionId(String executionId);

  List<CallbackReconciliationRecord> findDue(Instant now, int limit);

  /** Claim condicional com lease. Retorna empty se perdeu a disputa. */
  Optional<CallbackReconciliationRecord> claim(
      String reconciliationId,
      long expectedVersion,
      String workerId,
      Instant leaseUntil,
      Instant now);

  CallbackReconciliationRecord update(
      String reconciliationId,
      long expectedVersion,
      CallbackReconciliationState state,
      int queryCount,
      Instant nextQueryAt,
      CallbackDeliveryStatusDisposition lastDisposition,
      String externalDeliveryRef,
      String leaseOwner,
      Instant leaseUntil,
      Instant now);

  List<CallbackReconciliationRecord> findExpiredLeases(Instant now);
}
