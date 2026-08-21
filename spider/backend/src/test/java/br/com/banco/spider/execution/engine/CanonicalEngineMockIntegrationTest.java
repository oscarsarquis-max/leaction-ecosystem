package br.com.banco.spider.execution.engine;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.canonical.validation.CanonicalStructuralValidator;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.mapping.ExplicitStepInputMapper;
import br.com.banco.spider.execution.persistence.support.InMemoryPersistenceBundle;
import br.com.banco.spider.execution.plan.DeterministicExecutionPlanMaterializer;
import br.com.banco.spider.execution.recovery.ExecutionRecoveryService;
import br.com.banco.spider.execution.retry.ConfiguredRetryPolicyCatalog;
import br.com.banco.spider.execution.retry.RetryPolicyDefinition;
import br.com.banco.spider.execution.route.CanonicalRouteFixtures;
import br.com.banco.spider.execution.route.DeterministicRouteResolver;
import br.com.banco.spider.execution.route.InMemoryRouteCatalog;
import br.com.banco.spider.execution.route.RouteDefinitionValidator;
import br.com.banco.spider.execution.step.IntermediateStepOutputStore;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.IntegrityDigestPort;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionRecoveryQuery;
import br.com.banco.spider.integration.binding.ConfiguredAdapterBindingResolver;
import br.com.banco.spider.integration.mock.MockUniversalAdapter;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import reactor.test.StepVerifier;

class CanonicalEngineMockIntegrationTest {

  @Test
  void endToEndWithRealMockAdapterAndPersistence() {
    Instant fixed = Instant.parse("2026-07-21T18:00:00Z");
    IdentifierGenerator ids = IdentifierGenerator.fixed(() -> "INT");
    InMemoryPersistenceBundle bundle = new InMemoryPersistenceBundle(SpiderClock.fixed(fixed), ids);

    var engine =
        new DefaultCanonicalExecutionEngine(
            new CanonicalStructuralValidator(),
            new DeterministicRouteResolver(
                new InMemoryRouteCatalog(
                    List.of(CanonicalRouteFixtures.publishedSingleStep("demo", 1))),
                new RouteDefinitionValidator()),
            new DeterministicExecutionPlanMaterializer(
                ids, SpiderClock.fixed(fixed), IntegrityDigestPort.sha256()),
            new ConfiguredAdapterBindingResolver(
                Map.of(
                    ConfiguredAdapterBindingResolver.DEFAULT_MOCK_BINDING,
                    new MockUniversalAdapter(new ObjectMapper()))),
            bundle.gateway,
            bundle.keyHash,
            bundle.retryExecutor,
            new ExplicitStepInputMapper(new ObjectMapper()),
            new ConfiguredRetryPolicyCatalog(
                List.of(RetryPolicyDefinition.publishedTechnical("default", "1.0", 2))),
            bundle.stepStore,
            new IntermediateStepOutputStore(),
            bundle.waitCreation,
            ids,
            SpiderClock.fixed(fixed));

    StepVerifier.create(engine.execute(CanonicalRouteFixtures.request("int-1", "idem", "SUCCESS")))
        .assertNext(
            result -> {
              assertEquals(ExecutionState.SUCCEEDED, result.state());
              assertEquals("demo", result.resolution().routeId());
            })
        .verifyComplete();

    assertTrue(bundle.planStore.findByExecutionId("int-1").isPresent());
    var recovery =
        new ExecutionRecoveryService(
            new InMemoryExecutionRecoveryQuery(bundle.controlStore, bundle.planStore),
            IntegrityDigestPort.sha256());
    assertTrue(recovery.verifyPlanIntegrity("int-1").ok());
  }
}
