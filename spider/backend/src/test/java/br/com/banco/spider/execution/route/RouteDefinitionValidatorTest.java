package br.com.banco.spider.execution.route;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.execution.mapping.StepInputMappingKind;
import java.util.List;
import org.junit.jupiter.api.Test;

class RouteDefinitionValidatorTest {

  private final RouteDefinitionValidator validator = new RouteDefinitionValidator();

  @Test
  void publishedValidRoutePasses() {
    assertTrue(validator.validate(CanonicalRouteFixtures.publishedSingleStep("r1", 10)).isEmpty());
  }

  @Test
  void linearTwoStepsValid() {
    assertTrue(validator.validate(CanonicalRouteFixtures.publishedLinearTwoSteps("r2", 10)).isEmpty());
  }

  @Test
  void draftIsIneligibleForSelection() {
    var errors = validator.validateForSelection(CanonicalRouteFixtures.draftRoute("r-draft"));
    assertTrue(errors.stream().anyMatch(e -> "ROUTE_NOT_PUBLISHED".equals(e.code())));
  }

  @Test
  void zeroStepsRejected() {
    RouteDefinition route =
        new RouteDefinition(
            "r0",
            "1.0.0",
            CanonicalRouteFixtures.JOURNEY,
            RouteStatus.PUBLISHED,
            "contract:in@1",
            "contract:out@1",
            new RouteTarget(CanonicalRouteFixtures.CAPABILITY, CanonicalRouteFixtures.OPERATION),
            1,
            List.of(),
            "integrity:r0@1");
    assertTrue(validator.validate(route).stream().anyMatch(e -> "ROUTE_STEPS_EMPTY".equals(e.code())));
  }

  @Test
  void branchRejected() {
    RouteStepDefinition root =
        RouteStepDefinition.entry(
            "a",
            CanonicalRouteFixtures.CAPABILITY,
            CanonicalRouteFixtures.OPERATION,
            CanonicalRouteFixtures.BINDING,
            "contract:in@1",
            "contract:out@1",
            null,
            null,
            null,
            IdempotencyClassification.OPTIONAL,
            null);
    RouteStepDefinition b =
        new RouteStepDefinition(
            "b",
            "X",
            "Y",
            CanonicalRouteFixtures.BINDING,
            "contract:in@1",
            "contract:out@1",
            List.of("a"),
            StepInputMappingKind.PREVIOUS_STEP_CANONICAL_DATA.toRef(),
            null,
            null,
            null,
            IdempotencyClassification.OPTIONAL,
            RetrySafety.SAFE,            null,            null);
    RouteStepDefinition c =
        new RouteStepDefinition(
            "c",
            "X",
            "Z",
            CanonicalRouteFixtures.BINDING,
            "contract:in@1",
            "contract:out@1",
            List.of("a"),
            StepInputMappingKind.PREVIOUS_STEP_CANONICAL_DATA.toRef(),
            null,
            null,
            null,
            IdempotencyClassification.OPTIONAL,
            RetrySafety.SAFE,            null,            null);
    RouteDefinition route =
        new RouteDefinition(
            "branch",
            "1.0.0",
            CanonicalRouteFixtures.JOURNEY,
            RouteStatus.PUBLISHED,
            "contract:in@1",
            "contract:out@1",
            new RouteTarget(CanonicalRouteFixtures.CAPABILITY, CanonicalRouteFixtures.OPERATION),
            1,
            List.of(root, b, c),
            "integrity:branch@1");
    assertFalse(validator.validate(route).isEmpty());
    assertTrue(
        validator.validate(route).stream()
            .anyMatch(e -> e.code().contains("BRANCH") || e.code().contains("JOIN")));
  }

  @Test
  void targetMismatchRejected() {
    RouteStepDefinition step =
        RouteStepDefinition.entry(
            "step-1",
            "OTHER",
            CanonicalRouteFixtures.OPERATION,
            CanonicalRouteFixtures.BINDING,
            "contract:in@1",
            "contract:out@1",
            null,
            null,
            null,
            IdempotencyClassification.OPTIONAL,
            null);
    RouteDefinition route =
        new RouteDefinition(
            "rm",
            "1.0.0",
            CanonicalRouteFixtures.JOURNEY,
            RouteStatus.PUBLISHED,
            "contract:in@1",
            "contract:out@1",
            new RouteTarget(CanonicalRouteFixtures.CAPABILITY, CanonicalRouteFixtures.OPERATION),
            1,
            List.of(step),
            "integrity:rm@1");
    assertTrue(
        validator.validate(route).stream().anyMatch(e -> "ROUTE_TARGET_MISMATCH".equals(e.code())));
  }

  @Test
  void physicalDetailRejected() {
    RouteStepDefinition step =
        RouteStepDefinition.entry(
            "step-1",
            CanonicalRouteFixtures.CAPABILITY,
            CanonicalRouteFixtures.OPERATION,
            "https://legacy.bank/api",
            "contract:in@1",
            "contract:out@1",
            null,
            null,
            null,
            IdempotencyClassification.OPTIONAL,
            null);
    RouteDefinition route =
        new RouteDefinition(
            "rp",
            "1.0.0",
            CanonicalRouteFixtures.JOURNEY,
            RouteStatus.PUBLISHED,
            "contract:in@1",
            "contract:out@1",
            new RouteTarget(CanonicalRouteFixtures.CAPABILITY, CanonicalRouteFixtures.OPERATION),
            1,
            List.of(step),
            "integrity:rp@1");
    assertTrue(
        validator.validate(route).stream()
            .anyMatch(e -> "ROUTE_PHYSICAL_DETAIL_FORBIDDEN".equals(e.code())));
  }

  @Test
  void retrySafetyIncompatibleRejected() {
    RouteStepDefinition step =
        new RouteStepDefinition(
            "step-1",
            CanonicalRouteFixtures.CAPABILITY,
            CanonicalRouteFixtures.OPERATION,
            CanonicalRouteFixtures.BINDING,
            "contract:in@1",
            "contract:out@1",
            List.of(),
            StepInputMappingKind.ROOT_REQUEST_CANONICAL_DATA.toRef(),
            null,
            null,
            null,
            IdempotencyClassification.NOT_SUPPORTED,
            RetrySafety.SAFE_WITH_IDEMPOTENCY_KEY,            null,            null);
    RouteDefinition route =
        new RouteDefinition(
            "rx",
            "1.0.0",
            CanonicalRouteFixtures.JOURNEY,
            RouteStatus.PUBLISHED,
            "contract:in@1",
            "contract:out@1",
            new RouteTarget(CanonicalRouteFixtures.CAPABILITY, CanonicalRouteFixtures.OPERATION),
            1,
            List.of(step),
            "integrity:rx@1");
    assertTrue(
        validator.validate(route).stream()
            .anyMatch(e -> "ROUTE_RETRY_SAFETY_INCOMPATIBLE".equals(e.code())));
  }

  @Test
  void publishedRequiresIntegrityRef() {
    RouteStepDefinition step =
        RouteStepDefinition.entry(
            "step-1",
            CanonicalRouteFixtures.CAPABILITY,
            CanonicalRouteFixtures.OPERATION,
            CanonicalRouteFixtures.BINDING,
            "contract:in@1",
            "contract:out@1",
            null,
            null,
            null,
            IdempotencyClassification.REQUIRED,
            null);
    RouteDefinition route =
        new RouteDefinition(
            "rx",
            "1.0.0",
            CanonicalRouteFixtures.JOURNEY,
            RouteStatus.PUBLISHED,
            "contract:in@1",
            "contract:out@1",
            new RouteTarget(CanonicalRouteFixtures.CAPABILITY, CanonicalRouteFixtures.OPERATION),
            1,
            List.of(step),
            null);
    assertTrue(
        validator.validate(route).stream().anyMatch(e -> "ROUTE_INTEGRITY_REQUIRED".equals(e.code())));
    assertEquals(IdempotencyClassification.REQUIRED, route.singleStep().idempotencyClassification());
  }

  @Test
  void maxStepsExceeded() {
    RouteDefinitionValidator tight = new RouteDefinitionValidator(1);
    assertFalse(tight.validate(CanonicalRouteFixtures.publishedLinearTwoSteps("r", 1)).isEmpty());
    assertTrue(
        tight.validate(CanonicalRouteFixtures.publishedLinearTwoSteps("r", 1)).stream()
            .anyMatch(e -> "ROUTE_STEPS_LIMIT".equals(e.code())));
  }
}
