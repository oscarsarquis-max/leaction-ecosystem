package br.com.banco.spider.execution.runtime;

import br.com.banco.spider.execution.domain.ExecutionState;
import java.util.List;

public interface ExecutionTransitionRecorderPort {

  ExecutionTransition record(
      ExecutionRuntimeState state, ExecutionState toState, String reasonCode);

  List<ExecutionTransition> findByExecutionId(String executionId);

  void clear();
}
