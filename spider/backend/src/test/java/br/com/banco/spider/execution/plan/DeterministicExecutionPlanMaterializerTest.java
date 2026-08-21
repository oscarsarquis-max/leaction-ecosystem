package br.com.banco.spider.execution.plan;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.execution.route.CanonicalRouteFixtures;
import br.com.banco.spider.execution.route.RouteResolution;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.IntegrityDigestPort;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class DeterministicExecutionPlanMaterializerTest {

  @Test
  void fixesVersionsAndUsesInjectedClockAndIds() {
    Instant fixed = Instant.parse("2026-07-21T12:00:00Z");
    AtomicInteger seq = new AtomicInteger();
    var materializer =
        new DeterministicExecutionPlanMaterializer(
            prefix -> prefix + "-DET-" + seq.incrementAndGet(),
            SpiderClock.fixed(fixed),
            IntegrityDigestPort.sha256());

    var route = CanonicalRouteFixtures.publishedSingleStep("route-a", "2.3.0", 10,
        br.com.banco.spider.execution.route.IdempotencyClassification.OPTIONAL);
    var request = CanonicalRouteFixtures.request("exec-42", "idem");
    var resolution = RouteResolution.selected(route, List.of("route-a@2.3.0"));

    var result = materializer.materialize(request, resolution);
    assertTrue(result.success());
    ExecutionPlan plan = result.plan();
    assertEquals("plan-DET-1", plan.planId());
    assertEquals(fixed, plan.createdAt());
    assertEquals("route-a", plan.routeRef().routeCode());
    assertEquals("2.3.0", plan.routeRef().routeVersion());
    assertTrue(plan.integrityRef().startsWith("sha256:"));
    assertThrows(UnsupportedOperationException.class, () -> plan.nodes().add(plan.nodes().getFirst()));
  }

  @Test
  void digestIsStableForSameCanonicalRepresentation() {
    Instant fixed = Instant.parse("2026-07-21T12:00:00Z");
    var materializer =
        new DeterministicExecutionPlanMaterializer(
            IdentifierGenerator.fixed(() -> "FIXED"),
            SpiderClock.fixed(fixed),
            IntegrityDigestPort.sha256());
    var route = CanonicalRouteFixtures.publishedSingleStep("r", 1);
    var request = CanonicalRouteFixtures.request("e", "i");
    var resolution = RouteResolution.selected(route, List.of("r@1.0.0"));
    String d1 = materializer.materialize(request, resolution).plan().integrityRef();
    String d2 = materializer.materialize(request, resolution).plan().integrityRef();
    assertEquals(d1, d2);
  }

  @Test
  void missingResolutionFails() {
    var materializer =
        new DeterministicExecutionPlanMaterializer(
            IdentifierGenerator.uuid(), SpiderClock.systemUtc(), IntegrityDigestPort.sha256());
    var request = CanonicalRouteFixtures.request("e", "i");
    var failed =
        materializer.materialize(
            request,
            RouteResolution.rejected(
                br.com.banco.spider.execution.route.RouteResolutionReasonCode.ROUTE_NOT_FOUND,
                List.of(),
                List.of(),
                "none"));
    assertTrue(!failed.success());
  }

  @Test
  void mutatingRouteAfterMaterializationDoesNotAffectPlan() {
    Instant fixed = Instant.parse("2026-07-21T12:00:00Z");
    var materializer =
        new DeterministicExecutionPlanMaterializer(
            IdentifierGenerator.fixed(() -> "X"),
            SpiderClock.fixed(fixed),
            IntegrityDigestPort.sha256());
    List<br.com.banco.spider.execution.route.RouteStepDefinition> mutableSteps =
        new ArrayList<>(CanonicalRouteFixtures.publishedSingleStep("r", 1).steps());
    var route =
        new br.com.banco.spider.execution.route.RouteDefinition(
            "r",
            "1.0.0",
            CanonicalRouteFixtures.JOURNEY,
            br.com.banco.spider.execution.route.RouteStatus.PUBLISHED,
            "contract:route-in@1.0",
            "contract:route-out@1.0",
            new br.com.banco.spider.execution.route.RouteTarget(
                CanonicalRouteFixtures.CAPABILITY, CanonicalRouteFixtures.OPERATION),
            1,
            mutableSteps,
            "integrity:r@1");
    var plan =
        materializer
            .materialize(
                CanonicalRouteFixtures.request("e", "i"),
                RouteResolution.selected(route, List.of("r@1.0.0")))
            .plan();
    String before = plan.nodes().getFirst().adapterBindingRef();
    // RouteDefinition already copied steps; clearing source list must not affect plan
    mutableSteps.clear();
    assertEquals(before, plan.nodes().getFirst().adapterBindingRef());
    assertEquals(1, plan.nodes().size());
    assertNotEquals(0, plan.integrityRef().length());
  }
}
