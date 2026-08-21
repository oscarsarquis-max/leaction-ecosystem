package br.com.banco.spider.execution.signal;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.application.security.AuthorizationDecision;
import br.com.banco.spider.execution.route.CanonicalRouteFixtures;
import br.com.banco.spider.execution.route.RouteDefinition;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import br.com.banco.spider.governance.AdapterKind;
import br.com.banco.spider.governance.BindingDescriptor;
import br.com.banco.spider.governance.DefaultActiveGovernanceSnapshotProvider;
import br.com.banco.spider.governance.DefaultHistoricalGovernanceContextLoader;
import br.com.banco.spider.governance.ExecutionGovernanceFixation;
import br.com.banco.spider.governance.GovernanceApprovalPolicy;
import br.com.banco.spider.governance.GovernanceArtifact;
import br.com.banco.spider.governance.GovernanceArtifactCodecRegistry;
import br.com.banco.spider.governance.GovernanceArtifactDigestService;
import br.com.banco.spider.governance.GovernanceArtifactType;
import br.com.banco.spider.governance.GovernanceControlPlaneService;
import br.com.banco.spider.governance.GovernanceLifecycleState;
import br.com.banco.spider.governance.GovernanceMode;
import br.com.banco.spider.governance.GovernanceScope;
import br.com.banco.spider.governance.GovernanceSnapshotCompiler;
import br.com.banco.spider.governance.GovernanceValidationService;
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
 * Wait fixado em snapshot v1; active v2 com Signal Definition distinta não altera lookup histórico.
 */
class SignalIngressHistoricalV1VsV2Test {

  private static final Instant NOW = Instant.parse("2026-08-21T21:00:00Z");

  private InMemoryGovernanceStores stores;
  private InMemoryExecutionGovernanceFixationStore fixations;
  private GovernanceControlPlaneService cps;
  private DefaultHistoricalGovernanceContextLoader loader;
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
    var snapshotProvider =
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

    snapV1 = publishWithSignal("route-sig-v1", "bundle:sig-v1", "1.0.0", "sig-v1");
    cps.activateSnapshot("activator", GovernanceScope.DEFAULT, snapV1.snapshotId(), "V1");
    snapV2 = publishWithSignal("route-sig-v2", "bundle:sig-v2", "2.0.0", "sig-v2");
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
  void historicalContextKeepsV1SignalDefinitionAfterV2Activation() {
    fixations.insert(
        new ExecutionGovernanceFixation(
            "exec-sig-1",
            GovernanceMode.CONTROL_PLANE,
            "DEFAULT",
            snapV1.snapshotId(),
            "bundle:sig-v1",
            "1.0.0",
            snapV1.bundleDigest(),
            snapV1.snapshotDigest(),
            1L,
            NOW));

    assertNotEquals(snapV1.snapshotId(), snapV2.snapshotId());
    assertEquals(
        snapV2.snapshotId(),
        stores.findActive(GovernanceScope.DEFAULT).orElseThrow().activeSnapshotId());

    StepVerifier.create(loader.loadForExecution("exec-sig-1"))
        .assertNext(
            ctx -> {
              assertEquals(snapV1.snapshotId(), ctx.snapshotId());
              assertTrue(
                  ctx.externalSignalDefinitionCatalog()
                      .findByExactRef("signal:sig-v1@1.0.0")
                      .isPresent());
              assertTrue(
                  ctx.externalSignalDefinitionCatalog()
                      .findByExactRef("signal:sig-v2@2.0.0")
                      .isEmpty());
            })
        .verifyComplete();
  }

  private ActiveGovernanceSnapshot publishWithSignal(
      String routeCode, String bundleCode, String ver, String signalCode) {
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

    ExternalSignalDefinition signal =
        ExternalSignalDefinition.publishedMock(
            signalCode, ver, "contract:signal:async-completion@1.0", "profile:signal:test@1.0");
    GovernanceArtifact sArt =
        cps.registerTyped(
            "author",
            GovernanceArtifactType.EXTERNAL_SIGNAL_DEFINITION,
            signal.signalCode(),
            signal.version(),
            "1.0",
            codecs.canonicalize(GovernanceArtifactType.EXTERNAL_SIGNAL_DEFINITION, signal));
    cps.validateArtifact("author", sArt.artifactId());
    cps.publishArtifact("publisher", sArt.artifactId());

    var bundle =
        cps.createBundle(
            "author",
            bundleCode,
            ver,
            GovernanceScope.DEFAULT,
            List.of(art.artifactRef(), bArt.artifactRef(), sArt.artifactRef()));
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
