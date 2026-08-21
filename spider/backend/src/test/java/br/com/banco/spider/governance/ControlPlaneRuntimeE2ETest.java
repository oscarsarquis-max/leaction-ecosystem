package br.com.banco.spider.governance;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.application.security.AuthorizationDecision;
import br.com.banco.spider.canonical.validation.CanonicalStructuralValidator;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.mapping.ExplicitStepInputMapper;
import br.com.banco.spider.execution.engine.DefaultCanonicalExecutionEngine;
import br.com.banco.spider.execution.persistence.support.InMemoryPersistenceBundle;
import br.com.banco.spider.execution.plan.DeterministicExecutionPlanMaterializer;
import br.com.banco.spider.execution.retry.EmptyRetryPolicyCatalog;
import br.com.banco.spider.execution.route.CanonicalRouteFixtures;
import br.com.banco.spider.execution.route.DeterministicRouteResolver;
import br.com.banco.spider.execution.route.InMemoryRouteCatalog;
import br.com.banco.spider.execution.route.RouteDefinition;
import br.com.banco.spider.execution.route.RouteDefinitionValidator;
import br.com.banco.spider.execution.step.IntermediateStepOutputStore;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.IntegrityDigestPort;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.governance.port.ExecutionGovernanceFixationStorePort;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionGovernanceFixationStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryGovernanceStores;
import br.com.banco.spider.integration.binding.ConfiguredAdapterBindingResolver;
import br.com.banco.spider.integration.mock.MockUniversalAdapter;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

/** E2E interno CONTROL_PLANE → snapshot → fixation → Mock Adapter. */
class ControlPlaneRuntimeE2ETest {

  @Test
  void controlPlanePublishedRouteExecutesWithFixation() {
    Instant fixed = Instant.parse("2026-08-21T21:00:00Z");
    SpiderClock clock = SpiderClock.fixed(fixed);
    AtomicLong seq = new AtomicLong();
    IdentifierGenerator ids = IdentifierGenerator.fixed(() -> String.valueOf(seq.incrementAndGet()));

    InMemoryGovernanceStores stores = new InMemoryGovernanceStores();
    GovernanceArtifactCodecRegistry codecs = new GovernanceArtifactCodecRegistry();
    GovernanceArtifactDigestService digests = new GovernanceArtifactDigestService();
    DefaultActiveGovernanceSnapshotProvider snapshotProvider =
        new DefaultActiveGovernanceSnapshotProvider(
            stores, stores, digests, GovernanceScope.DEFAULT, true);
    GovernanceControlPlaneService cps =
        new GovernanceControlPlaneService(
            (op, actor) -> Mono.just(AuthorizationDecision.PERMIT),
            stores,
            stores,
            stores,
            stores,
            stores,
            stores,
            codecs,
            digests,
            new GovernanceValidationService(stores, digests, codecs, ids, clock),
            new GovernanceSnapshotCompiler(stores, codecs, digests, ids, clock),
            snapshotProvider,
            new GovernanceApprovalPolicy(true, false),
            ids,
            clock,
            262144);

    RouteDefinition route = CanonicalRouteFixtures.publishedSingleStep("cp-demo", 10);
    GovernanceArtifact routeArt =
        cps.registerTyped(
            "author",
            GovernanceArtifactType.ROUTE_DEFINITION,
            route.routeCode(),
            route.version(),
            "1.0",
            codecs.canonicalize(GovernanceArtifactType.ROUTE_DEFINITION, route));
    cps.validateArtifact("author", routeArt.artifactId());
    cps.publishArtifact("publisher", routeArt.artifactId());

    BindingDescriptor binding =
        new BindingDescriptor(
            "binding:mock-universal",
            "1.0",
            AdapterKind.MOCK,
            List.of("contract:in@1"),
            List.of(CanonicalRouteFixtures.OPERATION),
            List.of(),
            List.of(),
            List.of("MOCK"),
            GovernanceLifecycleState.PUBLISHED);
    GovernanceArtifact bindArt =
        cps.registerTyped(
            "author",
            GovernanceArtifactType.ADAPTER_BINDING_DESCRIPTOR,
            binding.bindingCode(),
            binding.version(),
            "1.0",
            codecs.canonicalize(GovernanceArtifactType.ADAPTER_BINDING_DESCRIPTOR, binding));
    cps.validateArtifact("author", bindArt.artifactId());
    cps.publishArtifact("publisher", bindArt.artifactId());

    GovernanceBundle bundle =
        cps.createBundle(
            "author",
            "bundle:cp-e2e",
            "1.0.0",
            GovernanceScope.DEFAULT,
            List.of(routeArt.artifactRef(), bindArt.artifactRef()));
    assertTrue(cps.validateBundle("author", bundle.bundleId()).passed());
    ActiveGovernanceSnapshot snapshot = cps.publishBundle("publisher", bundle.bundleId());
    assertTrue(stores.findActive(GovernanceScope.DEFAULT).isEmpty());
    cps.activateSnapshot("activator", GovernanceScope.DEFAULT, snapshot.snapshotId(), "GO_LIVE");

    ExecutionGovernanceFixationStorePort fixationStore =
        new InMemoryExecutionGovernanceFixationStore();
    MockUniversalAdapter mockAdapter = new MockUniversalAdapter(new ObjectMapper());
    DefaultGovernanceResolutionContextProvider govProvider =
        new DefaultGovernanceResolutionContextProvider(
            "CONTROL_PLANE",
            true,
            "DEFAULT",
            snapshotProvider,
            stores,
            stores,
            fixationStore,
            mockAdapter,
            emptyProvider(),
            emptyProvider(),
            clock);

    InMemoryPersistenceBundle persistence =
        new InMemoryPersistenceBundle(clock, ids);
    DefaultCanonicalExecutionEngine engine =
        new DefaultCanonicalExecutionEngine(
            new CanonicalStructuralValidator(),
            new DeterministicRouteResolver(
                new InMemoryRouteCatalog(List.of()), new RouteDefinitionValidator()),
            new DeterministicExecutionPlanMaterializer(
                ids, clock, IntegrityDigestPort.sha256()),
            new ConfiguredAdapterBindingResolver(Map.of()),
            persistence.gateway,
            persistence.keyHash,
            persistence.retryExecutor,
            new ExplicitStepInputMapper(new ObjectMapper()),
            new EmptyRetryPolicyCatalog(),
            persistence.stepStore,
            new IntermediateStepOutputStore(),
            persistence.waitCreation,
            ids,
            clock,
            Duration.ofSeconds(60),
            govProvider,
            new RouteDefinitionValidator());

    StepVerifier.create(
            engine.execute(CanonicalRouteFixtures.request("cp-exec-1", "idem-cp", "SUCCESS")))
        .assertNext(
            result -> {
              assertEquals(ExecutionState.SUCCEEDED, result.state());
              assertEquals("cp-demo", result.resolution().routeId());
            })
        .verifyComplete();

    ExecutionGovernanceFixation fixation =
        fixationStore.findByExecutionId("cp-exec-1").orElseThrow();
    assertEquals(snapshot.snapshotId(), fixation.snapshotId());
    assertEquals(snapshot.bundleDigest(), fixation.bundleDigest());
    assertEquals(1L, fixation.activationSequence());
    assertEquals(GovernanceMode.CONTROL_PLANE, fixation.governanceMode());
  }

  private static <T> ObjectProvider<T> emptyProvider() {
    return new ObjectProvider<>() {
      @Override
      public T getObject(Object... args) {
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

      @Override
      public T getObject() {
        return null;
      }
    };
  }
}
