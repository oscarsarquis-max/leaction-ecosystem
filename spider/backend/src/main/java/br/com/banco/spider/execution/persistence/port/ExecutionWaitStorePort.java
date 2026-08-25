package br.com.banco.spider.execution.persistence.port;

import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.execution.wait.WaitState;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

public interface ExecutionWaitStorePort {
  void insert(ExecutionWaitRecord wait);

  Optional<ExecutionWaitRecord> findByWaitId(String waitId);

  Optional<ExecutionWaitRecord> findActiveByExecutionAndStep(String executionId, String stepId);

  Optional<ExecutionWaitRecord> findByExternalOperationRef(String sourceRef, String externalOperationRef);

  Optional<ExecutionWaitRecord> findByContinuationTokenFingerprint(String fingerprintDigest);

  List<ExecutionWaitRecord> findByExecutionId(String executionId);

  ExecutionWaitRecord updateState(
      String waitId,
      WaitState expectedState,
      long expectedVersion,
      WaitState newState,
      String receivedMessageId,
      Instant resolvedAt,
      String resolutionReasonCode,
      Instant now);

  List<ExecutionWaitRecord> findExpiredWaiting(Instant now);

  List<ExecutionWaitRecord> findRecoverable();

  List<ExecutionWaitRecord> listActive(int maxResults);
}
