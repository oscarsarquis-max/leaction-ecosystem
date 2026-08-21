package br.com.banco.spider.application.console;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.model.ExecutionTransitionRecord;
import br.com.banco.spider.execution.persistence.model.PersistedExecutionPlan;
import br.com.banco.spider.execution.step.AttemptState;
import br.com.banco.spider.execution.step.ExecutionStepRecord;
import br.com.banco.spider.execution.step.StepAttemptRecord;
import br.com.banco.spider.execution.step.StepState;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionControlStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionPlanStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionStepStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionTransitionStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionWaitStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryStepAttemptStore;
import br.com.banco.spider.operational.readmodel.ListOperationalExecutionsQuery;
import br.com.banco.spider.operational.readmodel.OperationalRedactionService;
import br.com.banco.spider.operational.readmodel.OperationalTimelinePhase;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.BeansException;
import org.springframework.beans.factory.ObjectProvider;

class OperationalConsoleQueryServiceTest {

  private InMemoryExecutionControlStore control;
  private InMemoryExecutionPlanStore plan;
  private InMemoryExecutionStepStore steps;
  private InMemoryStepAttemptStore attempts;
  private InMemoryExecutionTransitionStore transitions;
  private InMemoryExecutionWaitStore waits;
  private OperationalConsoleQueryService service;

  @BeforeEach
  void setUp() {
    control = new InMemoryExecutionControlStore();
    plan = new InMemoryExecutionPlanStore();
    steps = new InMemoryExecutionStepStore();
    attempts = new InMemoryStepAttemptStore();
    transitions = new InMemoryExecutionTransitionStore();
    waits = new InMemoryExecutionWaitStore();
    service =
        new OperationalConsoleQueryService(
            control,
            plan,
            steps,
            attempts,
            transitions,
            waits,
            emptyProvider(),
            emptyProvider(),
            emptyProvider(),
            new OperationalRedactionService(),
            50,
            20,
            true);
  }

  private static <T> ObjectProvider<T> emptyProvider() {
    return new ObjectProvider<>() {
      @Override
      public T getObject() throws BeansException {
        return null;
      }

      @Override
      public T getObject(Object... args) throws BeansException {
        return null;
      }

      @Override
      public T getIfAvailable() {
        return null;
      }

      @Override
      public T getIfUnique() {
        return null;
      }
    };
  }

  @Test
  void listOrdersAndCapsPageSize() {
    Instant t0 = Instant.parse("2026-08-21T10:00:00Z");
    for (int i = 0; i < 5; i++) {
      insertControl("ex-" + i, t0.plusSeconds(i));
    }
    var page =
        service
            .list(
                new ListOperationalExecutionsQuery(
                    List.of(), null, null, null, false, null, null, 2))
            .block();
    assertNotNull(page);
    assertEquals(2, page.items().size());
    assertEquals("ex-4", page.items().get(0).executionId());
    assertEquals("ex-3", page.items().get(1).executionId());
  }

  @Test
  void detailAggregatesPlanStepsAttemptsAndTimeline() {
    Instant now = Instant.parse("2026-08-21T12:00:00Z");
    insertControl("ex-retry", now);
    plan.insert(
        new PersistedExecutionPlan(
            "plan-1",
            "ex-retry",
            "RETRY_THEN_SUCCESS",
            "1",
            "journey:mock",
            now,
            "integrity:n/a",
            "1.0",
            "{\"steps\":[\"s1\"]}"));
    steps.insertAll(
        List.of(
            new ExecutionStepRecord(
                "ex-retry",
                "s1",
                0,
                StepState.SUCCEEDED,
                1,
                null,
                null,
                null,
                now,
                now.plusSeconds(2),
                now.plusSeconds(2))));
    attempts.insert(
        new StepAttemptRecord(
            "a1",
            "ex-retry",
            "s1",
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
            "a2",
            "ex-retry",
            "s1",
            2,
            "inv-2",
            "binding:mock@1",
            now.plusSeconds(1),
            now.plusSeconds(6),
            now.plusSeconds(2),
            AttemptState.SUCCEEDED,
            null,
            null,
            null,
            "CERTAIN",
            List.of()));
    transitions.append(
        new ExecutionTransitionRecord(
            "tr1", "ex-retry", 1, ExecutionState.RECEIVED, ExecutionState.RUNNING, "START", now, null));
    transitions.append(
        new ExecutionTransitionRecord(
            "tr2",
            "ex-retry",
            2,
            ExecutionState.RUNNING,
            ExecutionState.SUCCEEDED,
            "DONE",
            now.plusSeconds(2),
            null));

    var detail = service.getDetail("ex-retry").block().orElseThrow();
    assertTrue(detail.plan().available());
    assertEquals(1, detail.steps().data().size());
    assertEquals(2, detail.steps().data().getFirst().attemptCount());
    assertTrue(detail.timeline().available());
    assertTrue(
        detail.timeline().data().stream()
            .anyMatch(e -> e.phase() == OperationalTimelinePhase.STEP_EXECUTION));
    assertTrue(
        detail.timeline().data().stream().anyMatch(e -> "ATTEMPT".equals(e.eventType())));
    assertEquals(2, detail.timeline().data().stream().filter(e -> "ATTEMPT".equals(e.eventType())).count());
    assertFalse(detail.summary().correlationRef().contains("corr-ex-retry-full"));
    assertTrue(detail.securityPosture().available());
    assertEquals("REDACTED", detail.securityPosture().data().dataExposure());
  }

  private void insertControl(String id, Instant started) {
    control.insert(
        new ExecutionControlRecord(
            id,
            "ctx-" + id,
            "corr-" + id + "-full-value-xxxxxxxx",
            "plan-" + id,
            "ROUTE_A",
            "1",
            ExecutionState.SUCCEEDED,
            1,
            TechnicalStatus.SUCCESS,
            started,
            started.plusSeconds(1),
            started.plusSeconds(1),
            null,
            "retention:technical-default@1",
            "owner:hidden"));
  }
}
