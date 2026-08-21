package br.com.banco.spider.execution.persistence.port;

import br.com.banco.spider.execution.step.StepAttemptRecord;
import java.util.List;
import java.util.Optional;

public interface StepAttemptStorePort {
  void insert(StepAttemptRecord attempt);

  void update(StepAttemptRecord attempt);

  Optional<StepAttemptRecord> findByAttemptId(String attemptId);

  List<StepAttemptRecord> findByExecutionAndStep(String executionId, String stepId);

  int nextAttemptNumber(String executionId, String stepId);
}
