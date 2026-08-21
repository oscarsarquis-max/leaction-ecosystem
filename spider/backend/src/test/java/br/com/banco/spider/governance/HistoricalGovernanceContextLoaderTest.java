package br.com.banco.spider.governance;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.application.security.AuthorizationDecision;
import br.com.banco.spider.execution.route.CanonicalRouteFixtures;
import br.com.banco.spider.execution.route.RouteDefinition;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionGovernanceFixationStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryGovernanceRevocationRegistry;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryGovernanceStores;
import br.com.banco.spider.integration.mock.MockUniversalAdapter;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

class HistoricalGovernanceContextLoaderTest {

  private static final Instant NOW = Instant.parse("2026-08-21T22:00:00Z");

  private InMemoryGovernanceStores stores;
  private InMemoryExecutionGovernanceFixationStore fixations;
  private GovernanceControlPlaneService cps;
  private DefaultHistoricalGovernanceContextLoader loader;
  private DefaultActiveGovernanceSnapshotProvider snapshotProvider;
  private ActiveGovernanceSnapshot snapV1;
  private ActiveGovernanceSnapshot snapV2;

  @BeforeEach
  void setUp() {
    stores = new InMemoryGovernanceStores();
    fixations = new InMemoryExecutionGovernanceFixationStore();
    GovernanceArtifactCodecRegistry codecs = new GovernanceArtifactCodecRegistry();
    GovernanceArtifactDigestService digests = new GovernanceArtifactDigestService();
    SpiderClock clock = SpiderClock.fixed(NOW);
    AtomicLong seq = new AtomicLong();
    IdentifierGenerator ids = IdentifierGenerator.fixed(() -> String.valueOf(seq.incrementAndGet()));
    snapshotProvider =
        new DefaultActiveGovernanceSnapshotProvider(
            stores, stores, digests, GovernanceScope.DEFAULT, true);
    cps =
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

    snapV1 = publishRouteBundle(codecs, "cp-v1", "bundle:hist-v1", "1.0.0");
    cps.activateSnapshot("activator", GovernanceScope.DEFAULT, snapV1.snapshotId(), "V1");
    snapV2 = publishRouteBundle(codecs, "cp-v2", "bundle:hist-v2", "2.0.0");
    cps.activateSnapshot("activator", GovernanceScope.DEFAULT, snapV2.snapshotId(), "V2");

    loader =
        new DefaultHistoricalGovernanceContextLoader(
            fixations,
            stores,
            digests,
            emptyProvider(),
            emptyProvider(),
            emptyProvider(),
            new MockUniversalAdapter(new ObjectMapper()),
            emptyProvider(),
            emptyProvider(),
            true,
            100);
  }

  @Test
  void loadUsesFixationNotActiveSnapshot() {
    fixations.insert(
        new ExecutionGovernanceFixation(
            "exec-hist-1",
            GovernanceMode.CONTROL_PLANE,
            "DEFAULT",
            snapV1.snapshotId(),
            "bundle:hist-v1",
            "1.0.0",
            snapV1.bundleDigest(),
            snapV1.snapshotDigest(),
            1L,
            NOW));

    StepVerifier.create(loader.loadForExecution("exec-hist-1"))
        .assertNext(
            ctx -> {
              assertEquals(snapV1.snapshotId(), ctx.snapshotId());
              assertEquals(snapV1.bundleDigest(), ctx.bundleDigest());
              assertTrue(ctx.routeCatalog() != null);
            })
        .verifyComplete();

    // active is v2
    assertEquals(
        snapV2.snapshotId(),
        stores.findActive(GovernanceScope.DEFAULT).orElseThrow().activeSnapshotId());
  }

  @Test
  void missingFixationFailsClosed() {
    StepVerifier.create(loader.loadForExecution("missing"))
        .expectErrorMatches(
            ex ->
                ex instanceof GovernanceContextException g
                    && "GOVERNANCE_FIXATION_NOT_FOUND".equals(g.reasonCode()))
        .verify();
  }

  @Test
  void revocationStopsBeforeEffect() {
    InMemoryGovernanceRevocationRegistry registry = new InMemoryGovernanceRevocationRegistry();
    registry.markRevoked(snapV1.snapshotId(), "EMERGENCY");
    GovernanceInFlightDecisionService decisions =
        new GovernanceInFlightDecisionService(
            registry, true, "STOP_BEFORE_NEXT_EXTERNAL_EFFECT");
    GovernanceExecutionReference ref =
        new GovernanceExecutionReference(
            "e1",
            GovernanceMode.CONTROL_PLANE,
            snapV1.snapshotId(),
            "bundle:hist-v1@1.0.0",
            snapV1.bundleDigest(),
            1L,
            NOW);
    assertEquals(
        GovernanceInFlightDecision.STOP_BEFORE_EFFECT,
        decisions.decide(ref, GovernedEffectType.CALLBACK_DELIVERY, null));
  }

  private ActiveGovernanceSnapshot publishRouteBundle(
      GovernanceArtifactCodecRegistry codecs, String routeCode, String bundleCode, String ver) {
    RouteDefinition route = CanonicalRouteFixtures.publishedSingleStep(routeCode, 10);
    GovernanceArtifact art =
        cps.registerTyped(
            "author",
            GovernanceArtifactType.ROUTE_DEFINITION,
            route.routeCode(),
            route.version(),
            "1.0",
            codecs.canonicalize(GovernanceArtifactType.ROUTE_DEFINITION, route));
    cps.validateArtifact("author", art.artifactId());
    cps.publishArtifact("publisher", art.artifactId());
    BindingDescriptor binding =
        new BindingDescriptor(
            "binding:mock-universal",
            ver,
            AdapterKind.MOCK,
            List.of(),
            List.of(),
            List.of(),
            List.of(),
            List.of("MOCK"),
            GovernanceLifecycleState.PUBLISHED);
    // unique binding version per bundle to avoid conflict
    GovernanceArtifact bArt =
        cps.registerTyped(
            "author",
            GovernanceArtifactType.ADAPTER_BINDING_DESCRIPTOR,
            binding.bindingCode(),
            binding.version(),
            "1.0",
            codecs.canonicalize(GovernanceArtifactType.ADAPTER_BINDING_DESCRIPTOR, binding));
    cps.validateArtifact("author", bArt.artifactId());
    cps.publishArtifact("publisher", bArt.artifactId());
    var bundle =
        cps.createBundle(
            "author",
            bundleCode,
            ver,
            GovernanceScope.DEFAULT,
            List.of(art.artifactRef(), bArt.artifactRef()));
    assertTrue(cps.validateBundle("author", bundle.bundleId()).passed());
    return cps.publishBundle("publisher", bundle.bundleId());
  }

  private static <T> ObjectProvider<T> emptyProvider() {
    return new ObjectProvider<>() {
      @Override
      public T getObject() {
        return null;
      }

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
    };
  }
}
