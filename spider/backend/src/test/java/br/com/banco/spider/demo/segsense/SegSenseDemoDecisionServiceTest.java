package br.com.banco.spider.demo.segsense;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import br.com.banco.spider.satellite.SatelliteContractV1Test;
import br.com.banco.spider.satellite.application.SatelliteInteractionService;
import br.com.banco.spider.satellite.application.SatelliteRegistry;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ResultItem;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Mono;

class SegSenseDemoDecisionServiceTest {

  private ProviderCapabilityPort providers;
  private SegSenseDemoDecisionService service;

  @BeforeEach
  void setUp() {
    providers = mock(ProviderCapabilityPort.class);
    service =
        new SegSenseDemoDecisionService(
            new SatelliteInteractionService(new SatelliteRegistry(SatelliteContractV1Test.properties()), providers, null));
  }

  @Test
  void demoSliceDelegatesToSatelliteContract() {
    when(providers.execute(any()))
        .thenReturn(
            Mono.just(
                new ExecutionResult(
                    true,
                    "COMPLETED",
                    "preq-1",
                    "insurance-provider-mock",
                    "ill-1",
                    "ILLUSTRATIVE_NOT_ICATU_CONTRACT",
                    SegSenseDemoDecisionService.WATERMARK,
                    List.of(new ResultItem("STEP", "Revisar", "JOURNEY_STEP", true)),
                    List.of("Pendência"))));
    var decision = service.decide(command("UNDERSTAND_FAMILY_PROTECTION_OPTIONS", "k-demo-ok")).block();
    assertEquals(200, decision.status());
    assertEquals("PRE_PROPOSAL_READY", decision.body().get("status"));
    assertEquals(true, decision.body().get("demoEndpointDeprecated"));
    assertEquals("SPIDER_SATELLITE_CONTRACT_V1", decision.body().get("decisionProvenance"));
    assertFalse(decision.body().containsKey("planId"));
  }

  @Test
  void missingOriginFailsClosedBeforeProvider() {
    var decision =
        service
            .decide(
                new SegSenseDemoDecisionService.Command(
                    SegSenseDemoDecisionService.CONTRACT_VERSION,
                    "SEGSENSE",
                    SegSenseDemoDecisionService.SCENARIO,
                    null,
                    "UNDERSTAND_FAMILY_PROTECTION_OPTIONS",
                    "11111111-1111-1111-1111-111111111111",
                    "k-missing-origin"))
            .block();
    assertEquals(400, decision.status());
    verify(providers, never()).execute(any());
  }

  @Test
  void rejectedObjectiveDoesNotCallProvider() {
    var decision = service.decide(command("REQUEST_BINDING_QUOTE", "k-demo-reject")).block();
    assertEquals("REJECTED", decision.body().get("status"));
    verify(providers, never()).execute(any());
  }

  private static SegSenseDemoDecisionService.Command command(String objective, String key) {
    return new SegSenseDemoDecisionService.Command(
        SegSenseDemoDecisionService.CONTRACT_VERSION,
        "SEGSENSE",
        SegSenseDemoDecisionService.SCENARIO,
        SegSenseDemoOriginSnapshot.governed(),
        objective,
        "11111111-1111-1111-1111-111111111111",
        key);
  }
}
