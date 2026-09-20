package br.com.banco.spider.application.console;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.execution.route.InMemoryRouteCatalog;
import br.com.banco.spider.execution.route.RouteDefinition;
import br.com.banco.spider.operational.failurelab.FailureLabRouteSupport;
import java.util.ArrayList;
import java.util.Set;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;
import reactor.test.StepVerifier;

class DemoCanonicalRouteSupportTest {

  @Test
  void publishesTheFiveMissingMonitorOperationsWithoutDuplicatingRetry() {
    Set<String> operations =
        DemoCanonicalRouteSupport.routes().stream()
            .map(route -> route.target().operationCode())
            .collect(Collectors.toSet());
    assertEquals(
        Set.of(
            "SUCCESS_MULTI_STEP",
            "BUSINESS_NEGATIVE",
            "WAIT_SIGNAL_RESUME",
            "CALLBACK_RECONCILIATION",
            "TECHNICAL_FAILURE"),
        operations);
    assertFalse(operations.contains("RETRY_THEN_SUCCESS"));
    assertTrue(
        DemoCanonicalRouteSupport.routes().stream()
            .anyMatch(route -> route.steps().size() > 1 && "SUCCESS_MULTI_STEP".equals(route.target().operationCode())));
  }

  @Test
  void mergedCatalogKeepsRetryAndAddsDemoOperations() {
    ArrayList<RouteDefinition> routes = new ArrayList<>(FailureLabRouteSupport.routes());
    routes.addAll(DemoCanonicalRouteSupport.routes());
    var catalog = new InMemoryRouteCatalog(routes);
    StepVerifier.create(catalog.findPublishedCandidates("journey:mock", "mock", "RETRY_THEN_SUCCESS"))
        .assertNext(found -> assertFalse(found.isEmpty()))
        .verifyComplete();
    StepVerifier.create(catalog.findPublishedCandidates("journey:mock", "mock", "SUCCESS_MULTI_STEP"))
        .assertNext(found -> assertEquals(1, found.size()))
        .verifyComplete();
    StepVerifier.create(catalog.findPublishedCandidates("journey:mock", "mock", "WAIT_SIGNAL_RESUME"))
        .assertNext(found -> assertEquals(1, found.size()))
        .verifyComplete();
  }
}
