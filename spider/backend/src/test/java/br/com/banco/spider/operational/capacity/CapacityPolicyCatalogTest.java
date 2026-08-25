package br.com.banco.spider.operational.capacity;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Duration;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;

/**
 * O catálogo é a única fonte de limites. Precedência ambígua precisa falhar de forma explícita: uma
 * decisão de admissão não pode depender da ordem de leitura do arquivo.
 */
class CapacityPolicyCatalogTest {

  private final CapacityPolicyCatalog catalog =
      new CapacityPolicyCatalog(new ObjectMapper().findAndRegisterModules());

  @Test
  void publishedCatalogDeclaresGlobalWorkerAndScheduleScopes() {
    List<CapacityPolicy> policies = catalog.policies();
    assertTrue(policies.size() >= 4, "catálogo demo deve declarar os escopos previstos");
    assertTrue(
        policies.stream().anyMatch(policy -> policy.scopeType() == CapacityScopeType.GLOBAL));
    assertTrue(
        policies.stream()
            .anyMatch(
                policy ->
                    policy.scopeType() == CapacityScopeType.WORKER_TYPE
                        && policy.scopeRef().equals("CALLBACK_DELIVERY")));
    assertTrue(
        policies.stream()
            .anyMatch(
                policy ->
                    policy.scopeType() == CapacityScopeType.WORKER_TYPE
                        && policy.scopeRef().equals("SIGNAL_APPLICATION")));
    assertTrue(
        policies.stream().anyMatch(policy -> policy.scopeType() == CapacityScopeType.SCHEDULE));
  }

  @Test
  void moreSpecificScopeWinsOverTheBroaderOne() {
    AdmissionRequest request =
        new AdmissionRequest(
            "worker-schedule:sched:callback-reconciliation@1",
            CapacityScopeType.SCHEDULE,
            "sched:callback-reconciliation@1",
            "CALLBACK_RECONCILIATION",
            "sched:callback-reconciliation@1",
            null,
            null,
            CapacityTestSupport.T0,
            "corr-test");

    CapacityPolicy resolved = catalog.resolve(request).orElseThrow();

    assertEquals(CapacityScopeType.SCHEDULE, resolved.scopeType());
    assertEquals("capacity:schedule:callback-reconciliation@1.0", resolved.ref());
  }

  @Test
  void workerScopeWinsWhenNoScheduleScopeIsDeclared() {
    AdmissionRequest request =
        new AdmissionRequest(
            "worker-schedule:sched:callback-delivery@1",
            CapacityScopeType.SCHEDULE,
            "sched:callback-delivery@1",
            "CALLBACK_DELIVERY",
            "sched:callback-delivery@1",
            null,
            null,
            CapacityTestSupport.T0,
            "corr-test");

    CapacityPolicy resolved = catalog.resolve(request).orElseThrow();

    assertEquals(CapacityScopeType.WORKER_TYPE, resolved.scopeType());
    assertEquals("CALLBACK_DELIVERY", resolved.scopeRef());
  }

  @Test
  void globalScopeAnswersWhenNothingMoreSpecificMatches() {
    AdmissionRequest request =
        new AdmissionRequest(
            "worker-schedule:sched:wait-expiry@1",
            CapacityScopeType.SCHEDULE,
            "sched:wait-expiry@1",
            "WAIT_EXPIRY",
            "sched:wait-expiry@1",
            null,
            null,
            CapacityTestSupport.T0,
            "corr-test");

    CapacityPolicy resolved = catalog.resolve(request).orElseThrow();

    assertEquals(CapacityScopeType.GLOBAL, resolved.scopeType());
  }

  @Test
  void higherPrecedenceWinsAmongScopesOfTheSameSpecificity() {
    CapacityPolicy low = worker("low", 10);
    CapacityPolicy high = worker("high", 20);
    AdmissionRequest request = workerRequest();

    Optional<CapacityPolicy> resolved =
        CapacityPolicyCatalog.resolve(List.of(low, high), request);

    assertEquals("capacity:worker:high@1.0", resolved.orElseThrow().ref());
  }

  @Test
  void tiedPrecedenceOnTheSameSpecificityIsRejected() {
    CapacityPolicy first = worker("first", 20);
    CapacityPolicy second = worker("second", 20);

    IllegalStateException ambiguous =
        assertThrows(
            IllegalStateException.class,
            () -> CapacityPolicyCatalog.resolve(List.of(first, second), workerRequest()));

    assertTrue(ambiguous.getMessage().contains("Ambiguous capacity policy precedence"));
  }

  @Test
  void duplicateScopeIsRejectedAtLoad() {
    CapacityPolicy first = worker("first", 20);
    CapacityPolicy duplicate = worker("second", 21);

    IllegalStateException duplicated =
        assertThrows(
            IllegalStateException.class,
            () -> new CapacityPolicyCatalog(List.of(first, duplicate)));

    assertTrue(duplicated.getMessage().contains("Duplicate capacity scope"));
  }

  @Test
  void conflictingPrecedenceInsideTheSameScopeTypeIsRejectedAtLoad() {
    CapacityPolicy callback =
        new CapacityPolicy(
            "capacity:worker:callback",
            "1.0",
            CapacityScopeType.WORKER_TYPE,
            "CALLBACK_DELIVERY",
            CapacityPolicyState.ACTIVE,
            CapacityTestSupport.limits(2, -1, -1, 0),
            0,
            Duration.ofMinutes(1),
            Duration.ZERO,
            1,
            30,
            true);
    CapacityPolicy signal =
        new CapacityPolicy(
            "capacity:worker:signal",
            "1.0",
            CapacityScopeType.WORKER_TYPE,
            "SIGNAL_APPLICATION",
            CapacityPolicyState.ACTIVE,
            CapacityTestSupport.limits(2, -1, -1, 0),
            0,
            Duration.ofMinutes(1),
            Duration.ZERO,
            1,
            30,
            true);

    IllegalStateException conflict =
        assertThrows(
            IllegalStateException.class, () -> new CapacityPolicyCatalog(List.of(callback, signal)));

    assertTrue(conflict.getMessage().contains("Conflicting capacity precedence"));
  }

  @Test
  void emptyCatalogIsRejected() {
    assertThrows(IllegalStateException.class, () -> new CapacityPolicyCatalog(List.of()));
  }

  @Test
  void policyIsResolvableByItsPublishedReference() {
    CapacityPolicy any = catalog.policies().getFirst();
    assertEquals(any, catalog.findByRef(any.ref()).orElseThrow());
    assertTrue(catalog.findByRef("capacity:does-not-exist@9.9").isEmpty());
  }

  private static CapacityPolicy worker(String code, int precedence) {
    return new CapacityPolicy(
        "capacity:worker:" + code,
        "1.0",
        CapacityScopeType.WORKER_TYPE,
        "CALLBACK_DELIVERY",
        CapacityPolicyState.ACTIVE,
        CapacityTestSupport.limits(2, -1, -1, 0),
        0,
        Duration.ofMinutes(1),
        Duration.ZERO,
        1,
        precedence,
        true);
  }

  private static AdmissionRequest workerRequest() {
    return new AdmissionRequest(
        "worker-schedule:sched:callback-delivery@1",
        CapacityScopeType.WORKER_TYPE,
        "CALLBACK_DELIVERY",
        "CALLBACK_DELIVERY",
        "sched:callback-delivery@1",
        null,
        null,
        CapacityTestSupport.T0,
        "corr-test");
  }
}
