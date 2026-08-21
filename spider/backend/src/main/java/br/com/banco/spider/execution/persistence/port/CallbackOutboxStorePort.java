package br.com.banco.spider.execution.persistence.port;

import br.com.banco.spider.execution.callback.CallbackOutboxRecord;
import br.com.banco.spider.execution.callback.CallbackOutboxState;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

public interface CallbackOutboxStorePort {

  /** Insert idempotent by logicalCallbackId; returns existing if duplicate. */
  CallbackOutboxRecord insertIdempotent(CallbackOutboxRecord record);

  Optional<CallbackOutboxRecord> findByOutboxId(String outboxId);

  Optional<CallbackOutboxRecord> findByLogicalCallbackId(String logicalCallbackId);

  Optional<CallbackOutboxRecord> findByExecutionId(String executionId);

  CallbackOutboxRecord claim(
      String outboxId,
      CallbackOutboxState expectedState,
      long expectedVersion,
      CallbackOutboxState newState,
      Instant now);

  List<CallbackOutboxRecord> findReady(Instant now, int limit);

  List<CallbackOutboxRecord> findInterruptedDispatching(Instant leaseExpiredBefore);

  CallbackOutboxRecord updateState(
      String outboxId,
      long expectedVersion,
      CallbackOutboxState newState,
      Instant nextAttemptAt,
      int attemptCount,
      String lastErrorCode,
      Instant now);
}
