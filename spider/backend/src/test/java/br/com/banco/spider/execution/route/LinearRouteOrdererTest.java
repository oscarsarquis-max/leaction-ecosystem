package br.com.banco.spider.execution.route;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import br.com.banco.spider.execution.mapping.StepInputMappingKind;
import java.util.List;
import org.junit.jupiter.api.Test;

class LinearRouteOrdererTest {

  @Test
  void orderIndependentOfInsertion() {
    RouteStepDefinition a =
        RouteStepDefinition.entry(
            "a", "CAP", "OP", "b@1", "in@1", "out@1", null, null, null,
            IdempotencyClassification.OPTIONAL, null);
    RouteStepDefinition b =
        new RouteStepDefinition(
            "b",
            "CAP2",
            "OP2",
            "b@1",
            "in@1",
            "out@1",
            List.of("a"),
            StepInputMappingKind.PREVIOUS_STEP_CANONICAL_DATA.toRef(),
            null,
            null,
            null,
            IdempotencyClassification.OPTIONAL,
            RetrySafety.SAFE,            null,            null);
    var ordered1 = LinearRouteOrderer.order(List.of(a, b));
    var ordered2 = LinearRouteOrderer.order(List.of(b, a));
    assertEquals(List.of("a", "b"), ordered1.stream().map(RouteStepDefinition::stepId).toList());
    assertEquals(List.of("a", "b"), ordered2.stream().map(RouteStepDefinition::stepId).toList());
  }

  @Test
  void cycleRejected() {
    RouteStepDefinition a =
        new RouteStepDefinition(
            "a",
            "CAP",
            "OP",
            "b@1",
            "in@1",
            "out@1",
            List.of("b"),
            StepInputMappingKind.PREVIOUS_STEP_CANONICAL_DATA.toRef(),
            null,
            null,
            null,
            IdempotencyClassification.OPTIONAL,
            RetrySafety.SAFE,            null,            null);
    RouteStepDefinition b =
        new RouteStepDefinition(
            "b",
            "CAP",
            "OP",
            "b@1",
            "in@1",
            "out@1",
            List.of("a"),
            StepInputMappingKind.PREVIOUS_STEP_CANONICAL_DATA.toRef(),
            null,
            null,
            null,
            IdempotencyClassification.OPTIONAL,
            RetrySafety.SAFE,            null,            null);
    assertThrows(
        LinearRouteOrderer.LinearOrderException.class,
        () -> LinearRouteOrderer.order(List.of(a, b)));
  }
}
