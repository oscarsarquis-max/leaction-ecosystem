package br.com.banco.spider.governance;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.application.security.AuthorizationDecision;
import br.com.banco.spider.execution.route.CanonicalRouteFixtures;
import br.com.banco.spider.execution.route.RouteDefinition;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.governance.catalog.SnapshotBackedRouteCatalog;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryGovernanceStores;
import java.time.Instant;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

class GovernanceControlPlaneTest {

  private static final Instant NOW = Instant.parse("2026-08-21T20:00:00Z");

  private InMemoryGovernanceStores stores;
  private GovernanceControlPlaneService cps;
  private GovernanceArtifactCodecRegistry codecs;
  private GovernanceArtifactDigestService digests;
  private DefaultActiveGovernanceSnapshotProvider provider;

  @BeforeEach
  void setUp() {
    stores = new InMemoryGovernanceStores();
    codecs = new GovernanceArtifactCodecRegistry();
    digests = new GovernanceArtifactDigestService();
    SpiderClock clock = SpiderClock.fixed(NOW);
    AtomicLong seq = new AtomicLong();
    IdentifierGenerator ids = IdentifierGenerator.fixed(() -> String.valueOf(seq.incrementAndGet()));
    GovernanceAuthorizationPort auth =
        (op, actor) -> Mono.just(AuthorizationDecision.PERMIT);
    provider =
        new DefaultActiveGovernanceSnapshotProvider(
            stores, stores, digests, GovernanceScope.DEFAULT, true);
    GovernanceValidationService validation =
        new GovernanceValidationService(stores, digests, codecs, ids, clock);
    GovernanceSnapshotCompiler compiler =
        new GovernanceSnapshotCompiler(stores, codecs, digests, ids, clock);
    cps =
        new GovernanceControlPlaneService(
            auth,
            stores,
            stores,
            stores,
            stores,
            stores,
            stores,
            codecs,
            digests,
            validation,
            compiler,
            provider,
            new GovernanceApprovalPolicy(true, false),
            ids,
            clock,
            262144);
  }

  @Test
  void floatingVersionRejected() {
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new GovernanceArtifactRef(
                GovernanceArtifactType.ROUTE_DEFINITION, "route:x", "latest"));
  }

  @Test
  void digestGoldenAndTamper() {
    String a =
        digests.digestArtifact(
            GovernanceArtifactType.ROUTE_DEFINITION, "r1", "1.0.0", "1.0", "{\"x\":1}");
    String b =
        digests.digestArtifact(
            GovernanceArtifactType.ROUTE_DEFINITION, "r1", "1.0.0", "1.0", "{\"x\":1}");
    String c =
        digests.digestArtifact(
            GovernanceArtifactType.ROUTE_DEFINITION, "r1", "1.0.0", "1.0", "{\"x\":2}");
    assertEquals(a, b);
    assertFalse(digests.secureEquals(a, c));
  }

  @Test
  void bindingRejectsUrlAndSecret() {
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new BindingDescriptor(
                "http://evil",
                "1.0",
                AdapterKind.MOCK,
                List.of(),
                List.of(),
                List.of(),
                List.of(),
                List.of(),
                GovernanceLifecycleState.PUBLISHED));
  }

  @Test
  void publishActivateAndSnapshotCatalog() {
    RouteDefinition route = CanonicalRouteFixtures.publishedSingleStep("gov-r1", 10);
    String content = codecs.canonicalize(GovernanceArtifactType.ROUTE_DEFINITION, route);
    GovernanceArtifact art =
        cps.registerTyped(
            "author",
            GovernanceArtifactType.ROUTE_DEFINITION,
            route.routeCode(),
            route.version(),
            "1.0",
            content);
    cps.validateArtifact("author", art.artifactId());
    cps.publishArtifact("publisher", art.artifactId());

    BindingDescriptor binding =
        new BindingDescriptor(
            "binding:mock-univ",
            "1.0",
            AdapterKind.MOCK,
            List.of("contract:in@1"),
            List.of("op"),
            List.of(),
            List.of("profile:sec@1"),
            List.of("MOCK"),
            GovernanceLifecycleState.PUBLISHED);
    String bContent =
        codecs.canonicalize(GovernanceArtifactType.ADAPTER_BINDING_DESCRIPTOR, binding);
    GovernanceArtifact bArt =
        cps.registerTyped(
            "author",
            GovernanceArtifactType.ADAPTER_BINDING_DESCRIPTOR,
            binding.bindingCode(),
            binding.version(),
            "1.0",
            bContent);
    cps.validateArtifact("author", bArt.artifactId());
    cps.publishArtifact("publisher", bArt.artifactId());

    GovernanceBundle bundle =
        cps.createBundle(
            "author",
            "bundle:demo",
            "1.0.0",
            GovernanceScope.DEFAULT,
            List.of(art.artifactRef(), bArt.artifactRef()));
    GovernanceValidationReport report = cps.validateBundle("author", bundle.bundleId());
    assertTrue(report.passed());

    ActiveGovernanceSnapshot snapshot = cps.publishBundle("publisher", bundle.bundleId());
    assertEquals(bundle.exactRef(), snapshot.bundleRef());

    // publish does not activate
    assertTrue(stores.findActive(GovernanceScope.DEFAULT).isEmpty());

    GovernanceActivation act =
        cps.activateSnapshot("activator", GovernanceScope.DEFAULT, snapshot.snapshotId(), "GO_LIVE");
    assertEquals(1L, act.activationSequence());

    SnapshotBackedRouteCatalog catalog = new SnapshotBackedRouteCatalog(snapshot);
    StepVerifier.create(
            catalog.findPublishedCandidates(
                route.journeyRef(),
                route.target().capabilityCode(),
                route.target().operationCode()))
        .assertNext(list -> assertFalse(list.isEmpty()))
        .verifyComplete();

    // idempotent re-activation of same snapshot
    GovernanceActivation again =
        cps.activateSnapshot("activator", GovernanceScope.DEFAULT, snapshot.snapshotId(), "AGAIN");
    assertEquals(act.activationSequence(), again.activationSequence());
  }

  @Test
  void validationErrorsBlockPublish() {
    GovernanceBundle bundle =
        cps.createBundle(
            "author",
            "bundle:bad",
            "1.0.0",
            GovernanceScope.DEFAULT,
            List.of(
                new GovernanceArtifactRef(
                    GovernanceArtifactType.ROUTE_DEFINITION, "missing-route", "1.0.0")));
    GovernanceValidationReport report = cps.validateBundle("author", bundle.bundleId());
    assertFalse(report.passed());
    assertThrows(IllegalStateException.class, () -> cps.publishBundle("publisher", bundle.bundleId()));
  }

  @Test
  void distinctPublisherRequired() {
    RouteDefinition route = CanonicalRouteFixtures.publishedSingleStep("gov-r2", 10);
    String content = codecs.canonicalize(GovernanceArtifactType.ROUTE_DEFINITION, route);
    GovernanceArtifact art =
        cps.registerTyped(
            "author",
            GovernanceArtifactType.ROUTE_DEFINITION,
            route.routeCode(),
            route.version(),
            "1.0",
            content);
    cps.validateArtifact("author", art.artifactId());
    GovernanceArtifact validated =
        stores.findArtifactById(art.artifactId()).orElseThrow();
    assertEquals(GovernanceLifecycleState.VALIDATED, validated.lifecycleState());
    cps.publishArtifact("publisher", art.artifactId());
    GovernanceBundle bundle =
        cps.createBundle(
            "author",
            "bundle:pol",
            "1.0.0",
            GovernanceScope.DEFAULT,
            List.of(art.artifactRef()));
    cps.validateBundle("author", bundle.bundleId());
    assertThrows(IllegalStateException.class, () -> cps.publishBundle("author", bundle.bundleId()));
  }

  @Test
  void validateDoesNotPublish() {
    RouteDefinition route = CanonicalRouteFixtures.publishedSingleStep("gov-r3", 10);
    String content = codecs.canonicalize(GovernanceArtifactType.ROUTE_DEFINITION, route);
    GovernanceArtifact art =
        cps.registerTyped(
            "author",
            GovernanceArtifactType.ROUTE_DEFINITION,
            route.routeCode(),
            route.version(),
            "1.0",
            content);
    GovernanceArtifact validated = cps.validateArtifact("author", art.artifactId());
    assertEquals(GovernanceLifecycleState.VALIDATED, validated.lifecycleState());
    assertThrows(IllegalStateException.class, () -> cps.publishArtifact("author", art.artifactId()));
  }

  @Test
  void denyByDefaultAuthorization() {
    GovernanceControlPlaneService denied =
        new GovernanceControlPlaneService(
            (op, actor) -> Mono.just(AuthorizationDecision.DENY),
            stores,
            stores,
            stores,
            stores,
            stores,
            stores,
            codecs,
            digests,
            new GovernanceValidationService(
                stores, digests, codecs, IdentifierGenerator.fixed(() -> "1"), SpiderClock.fixed(NOW)),
            new GovernanceSnapshotCompiler(
                stores, codecs, digests, IdentifierGenerator.fixed(() -> "1"), SpiderClock.fixed(NOW)),
            provider,
            GovernanceApprovalPolicy.conservative(),
            IdentifierGenerator.fixed(() -> "1"),
            SpiderClock.fixed(NOW),
            262144);
    assertThrows(
        Exception.class,
        () ->
            denied.registerTyped(
                "actor",
                GovernanceArtifactType.ROUTE_DEFINITION,
                "r",
                "1",
                "1.0",
                "{}"));
  }
}
