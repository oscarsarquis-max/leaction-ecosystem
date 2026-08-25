package br.com.banco.spider.execution.engine;

import static org.junit.jupiter.api.Assertions.assertEquals;

import br.com.banco.spider.canonical.validation.CanonicalStructuralValidator;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.mapping.ExplicitStepInputMapper;
import br.com.banco.spider.execution.persistence.support.InMemoryPersistenceBundle;
import br.com.banco.spider.execution.plan.DeterministicExecutionPlanMaterializer;
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
import br.com.banco.spider.integration.binding.ConfiguredAdapterBindingResolver;
import br.com.banco.spider.integration.mock.MockUniversalAdapter;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import reactor.test.StepVerifier;

class OperationalTelemetryDoesNotAffectEngineTest {

  @Test
  void throwingTelemetryPublisherDoesNotFailSuccessfulExecution() {
    Instant now = Instant.parse("2026-08-25T10:00:00Z");
    IdentifierGenerator ids = IdentifierGenerator.sequential("telemetry");
    InMemoryPersistenceBundle persistence =
        new InMemoryPersistenceBundle(SpiderClock.fixed(now), ids);
    var routes =
        List.of(CanonicalRouteFixtures.publishedSingleStep("telemetry-route", 1));
    DefaultCanonicalExecutionEngine engine =
        new DefaultCanonicalExecutionEngine(
            new CanonicalStructuralValidator(),
            new DeterministicRouteResolver(
                new InMemoryRouteCatalog(routes), new RouteDefinitionValidator()),
            new DeterministicExecutionPlanMaterializer(
                ids, SpiderClock.fixed(now), IntegrityDigestPort.sha256()),
            new ConfiguredAdapterBindingResolver(
                Map.of(
                    ConfiguredAdapterBindingResolver.DEFAULT_MOCK_BINDING,
                    new MockUniversalAdapter(new ObjectMapper()))),
            persistence.gateway,
            persistence.keyHash,
            persistence.retryExecutor,
            new ExplicitStepInputMapper(new ObjectMapper()),
            new ConfiguredRetryPolicyCatalog(
                List.of(RetryPolicyDefinition.publishedTechnical("default", "1.0", 3))),
            persistence.stepStore,
            new IntermediateStepOutputStore(),
            persistence.waitCreation,
            ids,
            SpiderClock.fixed(now));
    engine.setOperationalEventPublisher(
        draft -> {
          throw new IllegalStateException("telemetry unavailable");
        });

    StepVerifier.create(
            engine.execute(
                CanonicalRouteFixtures.request("exec-telemetry", "idem-telemetry", "SUCCESS")))
        .assertNext(result -> assertEquals(ExecutionState.SUCCEEDED, result.state()))
        .verifyComplete();
  }
}
