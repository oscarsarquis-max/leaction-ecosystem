package br.com.banco.spider.execution.route;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import java.util.List;
import org.junit.jupiter.api.Test;
import reactor.test.StepVerifier;

class DeterministicRouteResolverTest {

  private DeterministicRouteResolver resolver(List<RouteDefinition> routes) {
    return new DeterministicRouteResolver(new InMemoryRouteCatalog(routes), new RouteDefinitionValidator());
  }

  @Test
  void selectsSingleCandidate() {
    var r = CanonicalRouteFixtures.publishedSingleStep("only", 5);
    CanonicalExecutionRequest req = CanonicalRouteFixtures.request("e1", "idem-1");
    StepVerifier.create(resolver(List.of(r)).resolve(req))
        .assertNext(
            res -> {
              assertTrue(res.selected());
              assertEquals(RouteResolutionReasonCode.ROUTE_SELECTED, res.reasonCode());
              assertEquals("only", res.selectedRoute().routeCode());
            })
        .verifyComplete();
  }

  @Test
  void noCandidate() {
    CanonicalExecutionRequest req = CanonicalRouteFixtures.request("e1", "idem-1");
    StepVerifier.create(resolver(List.of()).resolve(req))
        .assertNext(
            res -> {
              assertFalse(res.selected());
              assertEquals(RouteResolutionReasonCode.ROUTE_NOT_FOUND, res.reasonCode());
            })
        .verifyComplete();
  }

  @Test
  void selectsHigherPriority() {
    var low = CanonicalRouteFixtures.publishedSingleStep("low", 1);
    var high = CanonicalRouteFixtures.publishedSingleStep("high", 100);
    CanonicalExecutionRequest req = CanonicalRouteFixtures.request("e1", "idem-1");
    StepVerifier.create(resolver(List.of(low, high)).resolve(req))
        .assertNext(res -> assertEquals("high", res.selectedRoute().routeCode()))
        .verifyComplete();
  }

  @Test
  void tieAtHighestPriorityIsAmbiguous() {
    var a = CanonicalRouteFixtures.publishedSingleStep("a", 50);
    var b = CanonicalRouteFixtures.publishedSingleStep("b", 50);
    CanonicalExecutionRequest req = CanonicalRouteFixtures.request("e1", "idem-1");
    StepVerifier.create(resolver(List.of(a, b)).resolve(req))
        .assertNext(
            res -> {
              assertFalse(res.selected());
              assertEquals(RouteResolutionReasonCode.ROUTE_AMBIGUOUS, res.reasonCode());
            })
        .verifyComplete();
  }

  @Test
  void insertionOrderDoesNotDecideWinner() {
    var first = CanonicalRouteFixtures.publishedSingleStep("first-inserted", 10);
    var second = CanonicalRouteFixtures.publishedSingleStep("second-inserted", 20);
    CanonicalExecutionRequest req = CanonicalRouteFixtures.request("e1", "idem-1");
    StepVerifier.create(resolver(List.of(first, second)).resolve(req))
        .assertNext(res -> assertEquals("second-inserted", res.selectedRoute().routeCode()))
        .verifyComplete();
    StepVerifier.create(resolver(List.of(second, first)).resolve(req))
        .assertNext(res -> assertEquals("second-inserted", res.selectedRoute().routeCode()))
        .verifyComplete();
  }

  @Test
  void draftCandidateIsInvalid() {
    var draft = CanonicalRouteFixtures.draftRoute("draft");
    // Catalog filters PUBLISHED only — draft never returned. Use published-invalid via integrity.
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
            IdempotencyClassification.OPTIONAL,
            null);
    RouteDefinition publishedMissingIntegrity =
        new RouteDefinition(
            "bad",
            "1.0.0",
            CanonicalRouteFixtures.JOURNEY,
            RouteStatus.PUBLISHED,
            "contract:in@1",
            "contract:out@1",
            new RouteTarget(CanonicalRouteFixtures.CAPABILITY, CanonicalRouteFixtures.OPERATION),
            1,
            List.of(step),
            null);
    CanonicalExecutionRequest req = CanonicalRouteFixtures.request("e1", "idem-1");
    StepVerifier.create(resolver(List.of(publishedMissingIntegrity, draft)).resolve(req))
        .assertNext(
            res -> {
              assertFalse(res.selected());
              assertEquals(RouteResolutionReasonCode.ROUTE_INVALID, res.reasonCode());
            })
        .verifyComplete();
  }

  @Test
  void targetMismatchFromCatalogFilterYieldsNotFound() {
    RouteDefinition otherTarget =
        new RouteDefinition(
            "other",
            "1.0.0",
            CanonicalRouteFixtures.JOURNEY,
            RouteStatus.PUBLISHED,
            "contract:in@1",
            "contract:out@1",
            new RouteTarget("OTHER", "OP"),
            1,
            List.of(
                RouteStepDefinition.entry(
                    "s",
                    "OTHER",
                    "OP",
                    CanonicalRouteFixtures.BINDING,
                    "contract:in@1",
                    "contract:out@1",
                    null,
                    null,
                    null,
                    IdempotencyClassification.OPTIONAL,
                    null)),
            "integrity:other@1");
    CanonicalExecutionRequest req = CanonicalRouteFixtures.request("e1", "idem-1");
    StepVerifier.create(resolver(List.of(otherTarget)).resolve(req))
        .assertNext(res -> assertEquals(RouteResolutionReasonCode.ROUTE_NOT_FOUND, res.reasonCode()))
        .verifyComplete();
  }
}
