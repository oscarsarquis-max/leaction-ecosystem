package br.com.banco.spider.execution.persistence.port;

import br.com.banco.spider.execution.step.ExecutionStepRecord;
import br.com.banco.spider.execution.step.StepState;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

public interface ExecutionStepStorePort {
  void insertAll(List<ExecutionStepRecord> steps);

  Optional<ExecutionStepRecord> find(String executionId, String stepId);

  List<ExecutionStepRecord> findByExecutionIdOrdered(String executionId);

  ExecutionStepRecord updateState(
      String executionId,
      String stepId,
      StepState expectedState,
      long expectedVersion,
      StepState newState,
      String activeAttemptId,
      String outputResultRef,
      String terminalErrorCode,
      Instant startedAt,
      Instant completedAt,
      Instant lastUpdatedAt);

  List<ExecutionStepRecord> findByStates(List<StepState> states);
}
