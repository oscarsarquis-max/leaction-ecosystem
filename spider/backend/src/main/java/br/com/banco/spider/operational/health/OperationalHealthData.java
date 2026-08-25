package br.com.banco.spider.operational.health;

import br.com.banco.spider.execution.callback.CallbackOutboxRecord;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.operational.events.OperationalEvent;
import java.util.List;

public record OperationalHealthData(
    List<ExecutionControlRecord> executions,
    List<ExecutionWaitRecord> activeWaits,
    List<CallbackOutboxRecord> callbacks,
    List<OperationalEvent> events) {
  public OperationalHealthData {
    executions = executions == null ? List.of() : List.copyOf(executions);
    activeWaits = activeWaits == null ? List.of() : List.copyOf(activeWaits);
    callbacks = callbacks == null ? List.of() : List.copyOf(callbacks);
    events = events == null ? List.of() : List.copyOf(events);
  }
}
