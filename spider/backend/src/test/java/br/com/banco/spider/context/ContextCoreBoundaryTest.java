package br.com.banco.spider.context;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verifyNoInteractions;

import br.com.banco.spider.application.canonical.SubmitCanonicalExecutionUseCase;
import br.com.banco.spider.application.security.AuthenticatedOriginator;
import br.com.banco.spider.context.application.ContextIntelligenceService;
import br.com.banco.spider.context.application.InMemoryContextDecisionStore;
import br.com.banco.spider.context.contract.IntentConstraints;
import br.com.banco.spider.context.contract.IntentContract;
import br.com.banco.spider.context.domain.ContextPolicyGuard;
import br.com.banco.spider.context.domain.DeterministicIntentRouter;
import br.com.banco.spider.context.domain.StaticBusinessIntentCatalog;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;

class ContextCoreBoundaryTest {

  @Test
  void unconfirmedDecisionNeverReachesCanonicalCore() {
    var fixture = fixture();
    var catalog = fixture.catalog();
    var service = fixture.service();
    var contract =
        catalog.findByIntent("INVESTIGATE_CREDIT_RELEASE").orElseThrow().businessCardContract();
    var originator = originator();

    var outcome = service.execute("unknown-preview", contract, originator).block();

    assertFalse(outcome.success());
    verifyNoInteractions(fixture.canonical());
  }

  @Test
  void policyRejectedMutationNeverReachesCanonicalCore() {
    var fixture = fixture();
    var base =
        fixture
            .catalog()
            .findByIntent("INVESTIGATE_CREDIT_RELEASE")
            .orElseThrow()
            .businessCardContract();
    var mutable =
        new IntentContract(
            base.schemaVersion(),
            base.intent(),
            base.domain(),
            base.objective(),
            base.entities(),
            new IntentConstraints(true, false, true),
            base.provenance(),
            base.confidence());
    var originator = originator();
    var preview = fixture.service().resolve(mutable, originator.principalRef());

    var outcome =
        fixture.service().execute(preview.decisionId(), mutable, originator).block();

    assertFalse(outcome.success());
    verifyNoInteractions(fixture.canonical());
  }

  private static Fixture fixture() {
    var catalog = new StaticBusinessIntentCatalog();
    var canonical = mock(SubmitCanonicalExecutionUseCase.class);
    var service =
        new ContextIntelligenceService(
            catalog,
            new ContextPolicyGuard(catalog),
            new DeterministicIntentRouter(catalog),
            new InMemoryContextDecisionStore(),
            canonical,
            OperationalEventPublisher.noop(),
            IdentifierGenerator.sequential("test"),
            SpiderClock.fixed(Instant.parse("2026-09-03T12:00:00Z")),
            new ObjectMapper().findAndRegisterModules());
    return new Fixture(catalog, canonical, service);
  }

  private static AuthenticatedOriginator originator() {
    return new AuthenticatedOriginator(
        "owner:test",
        "console-local-demo",
        "operational-console",
        "LOCAL_DEMO",
        Instant.parse("2026-09-03T11:00:00Z"),
        Instant.parse("2026-09-03T13:00:00Z"),
        List.of("mock"),
        "local-demo",
        "evidence:test");
  }

  private record Fixture(
      StaticBusinessIntentCatalog catalog,
      SubmitCanonicalExecutionUseCase canonical,
      ContextIntelligenceService service) {}
}
