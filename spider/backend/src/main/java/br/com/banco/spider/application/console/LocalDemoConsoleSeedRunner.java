package br.com.banco.spider.application.console;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.model.ExecutionTransitionRecord;
import br.com.banco.spider.execution.persistence.model.PersistedExecutionPlan;
import br.com.banco.spider.execution.persistence.port.ExecutionControlStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionPlanStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionStepStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionTransitionStorePort;
import br.com.banco.spider.execution.persistence.port.StepAttemptStorePort;
import br.com.banco.spider.execution.step.AttemptState;
import br.com.banco.spider.execution.step.ExecutionStepRecord;
import br.com.banco.spider.execution.step.StepAttemptRecord;
import br.com.banco.spider.execution.step.StepState;
import java.time.Instant;
import java.util.List;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

/** Seed idempotente somente sob local-demo — não é caminho de produção. */
@Component
@Profile("local-demo")
@ConditionalOnProperty(name = "spider.console.local-demo.enabled", havingValue = "true")
public class LocalDemoConsoleSeedRunner implements ApplicationRunner {

  public static final String DEMO_EXECUTION_ID = "demo-retry-001";

  private final ExecutionControlStorePort control;
  private final ExecutionPlanStorePort plan;
  private final ExecutionStepStorePort steps;
  private final StepAttemptStorePort attempts;
  private final ExecutionTransitionStorePort transitions;

  public LocalDemoConsoleSeedRunner(
      ExecutionControlStorePort control,
      ExecutionPlanStorePort plan,
      ExecutionStepStorePort steps,
      StepAttemptStorePort attempts,
      ExecutionTransitionStorePort transitions) {
    this.control = control;
    this.plan = plan;
    this.steps = steps;
    this.attempts = attempts;
    this.transitions = transitions;
  }

  @Override
  public void run(ApplicationArguments args) {
    if (control.findByExecutionId(DEMO_EXECUTION_ID).isPresent()) {
      return;
    }
    Instant now = Instant.parse("2026-08-21T18:00:00Z");
    control.insert(
        new ExecutionControlRecord(
            DEMO_EXECUTION_ID,
            "ctx-demo",
            "corr-demo-retry-001-full",
            "plan-demo",
            "RETRY_THEN_SUCCESS",
            "1",
            ExecutionState.SUCCEEDED,
            2,
            TechnicalStatus.SUCCESS,
            now,
            now.plusSeconds(3),
            now.plusSeconds(3),
            null,
            "retention:technical-default@1",
            "owner:local-demo"));
    plan.insert(
        new PersistedExecutionPlan(
            "plan-demo",
            DEMO_EXECUTION_ID,
            "RETRY_THEN_SUCCESS",
            "1",
            "journey:mock",
            now,
            "integrity:n/a",
            "1.0",
            "{\"ordered\":[\"step-a\"]}"));
    steps.insertAll(
        List.of(
            new ExecutionStepRecord(
                DEMO_EXECUTION_ID,
                "step-a",
                0,
                StepState.SUCCEEDED,
                1,
                null,
                null,
                null,
                now,
                now.plusSeconds(3),
                now.plusSeconds(3))));
    attempts.insert(
        new StepAttemptRecord(
            "demo-att-1",
            DEMO_EXECUTION_ID,
            "step-a",
            1,
            "inv-1",
            "binding:mock@1",
            now,
            now.plusSeconds(5),
            now.plusSeconds(1),
            AttemptState.FAILED,
            null,
            "TRANSIENT",
            true,
            "UNCERTAIN",
            List.of()));
    attempts.insert(
        new StepAttemptRecord(
            "demo-att-2",
            DEMO_EXECUTION_ID,
            "step-a",
            2,
            "inv-2",
            "binding:mock@1",
            now.plusSeconds(1),
            now.plusSeconds(6),
            now.plusSeconds(3),
            AttemptState.SUCCEEDED,
            null,
            null,
            null,
            "CERTAIN",
            List.of()));
    transitions.append(
        new ExecutionTransitionRecord(
            "demo-t1",
            DEMO_EXECUTION_ID,
            1,
            ExecutionState.RECEIVED,
            ExecutionState.RUNNING,
            "START",
            now,
            null));
    transitions.append(
        new ExecutionTransitionRecord(
            "demo-t2",
            DEMO_EXECUTION_ID,
            2,
            ExecutionState.RUNNING,
            ExecutionState.SUCCEEDED,
            "DONE",
            now.plusSeconds(3),
            null));
  }
}
