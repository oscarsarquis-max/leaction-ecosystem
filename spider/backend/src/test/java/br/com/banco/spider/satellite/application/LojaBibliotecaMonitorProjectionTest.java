package br.com.banco.spider.satellite.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import br.com.banco.spider.config.SatelliteContractProperties;
import br.com.banco.spider.config.SatelliteContractProperties.ProviderEntry;
import br.com.banco.spider.config.SatelliteContractProperties.SatelliteEntry;
import br.com.banco.spider.operational.events.OperationalEventType;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextBlock;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextSnapshot;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Contribution;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Objective;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Provenance;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Mono;

class LojaBibliotecaMonitorProjectionTest {

  @Test
  void emitsOriginCapabilityAndCompanyWithoutSecrets() {
    var captured = new ArrayList<br.com.banco.spider.operational.events.OperationalEventDraft>();
    ProviderCapabilityPort providers = mock(ProviderCapabilityPort.class);
    when(providers.execute(any()))
        .thenReturn(
            Mono.just(
                new ExecutionResult(
                    true,
                    "COMPLETED",
                    "preq-mon",
                    "actionhub-biblioteca",
                    "ord-1",
                    "ACTIONHUB_BIBLIOTECA",
                    SatelliteContractV1.WATERMARK_BIBLIOTECA,
                    List.of(),
                    List.of(),
                    Map.of(
                        "checkout_url",
                        "https://actionhub.com.br/dashboard?checkout=ord-1&email=ana@loja.test",
                        "order_id",
                        "ord-1"))));
    var service =
        new SatelliteInteractionService(new SatelliteRegistry(properties()), providers, captured::add);
    var outcome = service.interact("lojadepaes", request()).block();
    assertEquals(200, outcome.status());
    assertFalse(captured.isEmpty());
    boolean company = false;
    for (var event : captured) {
      Map<String, String> attrs = event.attributes().toMap();
      assertEquals("lojadepaes", attrs.get("originSatellite"));
      assertEquals("EXPERIENCE", attrs.get("role"));
      assertEquals("NOT_USED", attrs.get("aiUsage"));
      assertFalse(String.valueOf(attrs).contains("ana@"));
      assertFalse(String.valueOf(attrs).contains("secret"));
      if (event.eventType() == OperationalEventType.SATELLITE_COMPANY_AUTHORIZED) {
        company = BibliotecaStateProjection.MONITOR_COMPANY_ID.equals(attrs.get("companyId"))
            && "COMPANY_AUTHORIZED".equals(attrs.get("reasonCode"));
      }
      if (event.eventType() == OperationalEventType.SATELLITE_RESPONSE_RETURNED) {
        assertEquals(SatelliteContractV1.START_HUB_CATALOG_CHECKOUT, attrs.get("capabilityRef"));
        assertEquals(BibliotecaStateProjection.TECHNICAL_COMPLETED, attrs.get("technicalStatus"));
      }
    }
    assertTrue(company);
  }

  private static SatelliteContractProperties properties() {
    SatelliteContractProperties props = new SatelliteContractProperties();
    SatelliteEntry loja = new SatelliteEntry();
    loja.setRole("EXPERIENCE");
    loja.setStatus("ACTIVE");
    loja.setPurposes(List.of(SatelliteContractV1.PURPOSE_LOJA_BIBLIOTECA));
    loja.setInteractionTypes(List.of("QUERY_STATUS"));
    loja.setClassifications(List.of("INTERNAL"));
    loja.setGovernedContextIds(List.of(SatelliteContractV1.BIBLIOTECA_SOURCE));
    loja.setAllowedObjectives(List.of("START_LOJA_CHECKOUT"));
    loja.setAllowedAttributes(
        Map.of(
            "channel",
            List.of("LOJADEPAES"),
            "theme",
            List.of("biblioteca_plans"),
            "appId",
            List.of("lojadepaes"),
            "purposeVersion",
            List.of("biblioteca-v1")));
    loja.setMonitorCompanyId(BibliotecaStateProjection.MONITOR_COMPANY_ID);
    props.getRegistry().put("lojadepaes", loja);
    ProviderEntry provider = new ProviderEntry();
    provider.setRole("PROVIDER");
    provider.setStatus("TEST_DOUBLE");
    provider.setCapabilities(List.of(SatelliteContractV1.START_HUB_CATALOG_CHECKOUT));
    props.getProviders().put("actionhub-biblioteca", provider);
    return props;
  }

  private static SatelliteInteractionRequest request() {
    String now = "2026-10-08T22:00:00Z";
    return new SatelliteInteractionRequest(
        "1.5",
        "loja-msg-monitor-0001",
        "loja-corr-monitor-0001",
        "lojadepaes",
        "EXPERIENCE",
        "QUERY_STATUS",
        now,
        "idem-monitor-checkout",
        SatelliteContractV1.PURPOSE_LOJA_BIBLIOTECA,
        new Objective("START_LOJA_CHECKOUT", "SATELLITE_GOVERNED", now),
        new ContextBlock(
            null,
            new ContextSnapshot(
                "1.5",
                "INTERNAL",
                true,
                new Provenance(
                    "SATELLITE_GOVERNED",
                    SatelliteContractV1.BIBLIOTECA_SOURCE,
                    now,
                    "SERVER_REGISTRY",
                    "GOVERNED"),
                Map.of(
                    "channel",
                    "LOJADEPAES",
                    "theme",
                    "biblioteca_plans",
                    "appId",
                    "lojadepaes",
                    "purposeVersion",
                    "biblioteca-v1"),
                List.of(
                    new Contribution(
                        "GOVERNED_SOURCE",
                        "SATELLITE_GOVERNED",
                        SatelliteContractV1.BIBLIOTECA_SOURCE,
                        now,
                        "SERVER_REGISTRY",
                        "GOVERNED",
                        true,
                        Map.of("theme", "biblioteca_plans"))),
                "GOVERNED_SOURCE")),
        "INTERNAL",
        "SYNC",
        Map.of(),
        Map.of(
            "biblioteca",
            Map.of("appId", "lojadepaes", "subjectId", "cliente@loja.test", "sku", "LOJADEPAES_BIBLIOTECA_MENSAL")));
  }
}
