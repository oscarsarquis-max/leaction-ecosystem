package br.com.banco.spider.execution.runtime;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.execution.domain.ExecutionState;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/** Estado técnico transitório da execução (em memória neste incremento). */
public final class ExecutionRuntimeState {

  private final String executionId;
  private String planId;
  private ExecutionState executionState;
  private final Map<String, ExecutionState> stepStates;
  private final List<ExecutionTransition> transitionSequence;
  private Instant startedAt;
  private Instant completedAt;
  private final List<CanonicalError> errors;

  /** Cria estado sem transição inicial; a primeira transição deve ir para RECEIVED. */
  public ExecutionRuntimeState(String executionId) {
    this.executionId = Objects.requireNonNull(executionId, "executionId");
    this.executionState = null;
    this.stepStates = new LinkedHashMap<>();
    this.transitionSequence = new ArrayList<>();
    this.errors = new ArrayList<>();
  }

  public String executionId() {
    return executionId;
  }

  public String planId() {
    return planId;
  }

  public void planId(String planId) {
    this.planId = planId;
  }

  public ExecutionState executionState() {
    return executionState;
  }

  void apply(ExecutionTransition transition) {
    this.executionState = transition.toState();
    this.transitionSequence.add(transition);
    if (transition.toState() == ExecutionState.RUNNING && startedAt == null) {
      startedAt = transition.at();
    }
    if (transition.toState().isTerminal() || transition.toState() == ExecutionState.WAITING_EXTERNAL) {
      completedAt = transition.at();
    }
  }

  public void addError(CanonicalError error) {
    if (error != null) {
      errors.add(error);
    }
  }

  public void addErrors(List<CanonicalError> more) {
    if (more != null) {
      errors.addAll(more);
    }
  }

  public List<ExecutionTransition> transitions() {
    return List.copyOf(transitionSequence);
  }

  public List<CanonicalError> errors() {
    return List.copyOf(errors);
  }

  public Instant startedAt() {
    return startedAt;
  }

  public Instant completedAt() {
    return completedAt;
  }

  public Map<String, ExecutionState> stepStates() {
    return Map.copyOf(stepStates);
  }

  public void stepState(String stepId, ExecutionState state) {
    stepStates.put(stepId, state);
  }
}
