package br.com.banco.spider.governance;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.application.security.AuthorizationDecision;
import br.com.banco.spider.execution.route.CanonicalRouteFixtures;
import br.com.banco.spider.execution.route.RouteDefinition;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionGovernanceFixationStore;
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

/**
 * Prova: execução fixada em v1 ignora active v2; nova execution usaria active v2.
 */
class HistoricalGovernanceAsyncV1VsV2Test {

  private static final Instant NOW = Instant.parse("2026-08-21T23:00:00Z");

  private InMemoryGovernanceStores stores;
  private InMemoryExecutionGovernanceFixationStore fixations;
  private GovernanceControlPlaneService cps;
  private DefaultHistoricalGovernanceContextLoader loader;
  private DefaultActiveGovernanceSnapshotProvider snapshotProvider;
  private GovernanceArtifactCodecRegistry codecs;
  private ActiveGovernanceSnapshot snapV1;
  private ActiveGovernanceSnapshot snapV2;

  @BeforeEach
  void setUp() {
    stores = new InMemoryGovernanceStores();
    fixations = new InMemoryExecutionGovernanceFixationStore();
    codecs = new GovernanceArtifactCodecRegistry();
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

    snapV1 = publish("route-async-v1", "bundle:async-v1", "1.0.0");
    cps.activateSnapshot("activator", GovernanceScope.DEFAULT, snapV1.snapshotId(), "V1");
    snapV2 = publish("route-async-v2", "bundle:async-v2", "2.0.0");
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
  void inFlightExecutionKeepsV1AfterV2ActivationAndCacheEviction() {
    String executionId = "exec-async-v1";
    fixations.insert(
        new ExecutionGovernanceFixation(
            executionId,
            GovernanceMode.CONTROL_PLANE,
            "DEFAULT",
            snapV1.snapshotId(),
            "bundle:async-v1",
            "1.0.0",
            snapV1.bundleDigest(),
            snapV1.snapshotDigest(),
            1L,
            NOW));

    assertNotEquals(snapV1.snapshotId(), snapV2.snapshotId());
    assertEquals(
        snapV2.snapshotId(),
        stores.findActive(GovernanceScope.DEFAULT).orElseThrow().activeSnapshotId());

    loader.evict(snapV1.snapshotId());

    StepVerifier.create(loader.loadForExecution(executionId))
        .assertNext(
            ctx -> {
              assertEquals(snapV1.snapshotId(), ctx.snapshotId());
              assertEquals(snapV1.bundleDigest(), ctx.bundleDigest());
              assertNotEquals(snapV2.snapshotId(), ctx.snapshotId());
            })
        .verifyComplete();

    assertEquals(
        snapV2.snapshotId(),
        stores.findActive(GovernanceScope.DEFAULT).orElseThrow().activeSnapshotId());
  }

  private ActiveGovernanceSnapshot publish(String routeCode, String bundleCode, String ver) {
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
