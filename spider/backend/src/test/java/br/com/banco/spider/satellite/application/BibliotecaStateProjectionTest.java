package br.com.banco.spider.satellite.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextBlock;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextSnapshot;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Contribution;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Objective;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Provenance;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class BibliotecaStateProjectionTest {

  @Test
  void checkoutCreatedIsPendingNotConfirmedAndStripsEmail() {
    ExecutionResult provider =
        new ExecutionResult(
            true,
            "COMPLETED",
            "preq-checkout",
            "actionhub-biblioteca",
            "ord-1",
            "ACTIONHUB_BIBLIOTECA",
            SatelliteContractV1.WATERMARK_BIBLIOTECA,
            List.of(),
            List.of(),
            Map.of(
                "checkout_url",
                "https://actionhub.com.br/dashboard?checkout=ord-1&email=ana@loja.test&client=lojadepaes",
                "order_id",
                "ord-1",
                "sku",
                "LOJADEPAES_BIBLIOTECA_MENSAL",
                "checkout_mode",
                "subscription"));
    var projection =
        BibliotecaStateProjection.project(
            request("START_LOJA_CHECKOUT"),
            "READY",
            SatelliteContractV1.START_HUB_CATALOG_CHECKOUT,
            provider);
    assertEquals("READY", projection.states().get("satellite"));
    assertEquals(BibliotecaStateProjection.TECHNICAL_COMPLETED, projection.states().get("technical"));
    assertEquals("pending", projection.states().get("commercial"));
    assertEquals(BibliotecaStateProjection.FINANCIAL_PENDING, projection.states().get("financial"));
    assertEquals(SatelliteContractV1.GET_LOJA_ENTITLEMENTS, projection.nextInteraction());
    assertFalse(String.valueOf(projection.sanitizedSummary().get("checkout_url")).contains("ana@"));
    assertEquals(Boolean.TRUE, projection.sanitizedSummary().get("checkoutHostAllowed"));
    assertEquals("ord-1", projection.identities().get("actionHubOperationId"));
  }

  @Test
  void foreignCheckoutHostIsDroppedAndNotConfirmed() {
    ExecutionResult provider =
        new ExecutionResult(
            true,
            "COMPLETED",
            "preq-bad",
            "actionhub-biblioteca",
            null,
            "ACTIONHUB_BIBLIOTECA",
            SatelliteContractV1.WATERMARK_BIBLIOTECA,
            List.of(),
            List.of(),
            Map.of("checkout_url", "https://evil.example/pay?card=411111"));
    var projection =
        BibliotecaStateProjection.project(
            request("START_LOJA_CHECKOUT"),
            "READY",
            SatelliteContractV1.START_HUB_CATALOG_CHECKOUT,
            provider);
    assertNull(projection.sanitizedSummary().get("checkout_url"));
    assertEquals(Boolean.FALSE, projection.sanitizedSummary().get("checkoutHostAllowed"));
    assertFalse(projection.sanitizedSummary().containsKey("card"));
  }

  @Test
  void timeoutAfterPossibleCheckoutIsUnknownAndAsksSubscriptionQuery() {
    ExecutionResult provider =
        new ExecutionResult(
            false,
            "UNKNOWN",
            "preq-to",
            "actionhub-biblioteca",
            null,
            "ACTIONHUB_BIBLIOTECA",
            SatelliteContractV1.WATERMARK_BIBLIOTECA,
            List.of(),
            List.of(),
            Map.of("effectCertainty", "UNKNOWN"));
    var projection =
        BibliotecaStateProjection.project(
            request("START_LOJA_CHECKOUT"),
            "PROVIDER_UNAVAILABLE",
            SatelliteContractV1.START_HUB_CATALOG_CHECKOUT,
            provider);
    assertEquals(BibliotecaStateProjection.TECHNICAL_UNKNOWN, projection.states().get("technical"));
    assertEquals(BibliotecaStateProjection.FINANCIAL_UNKNOWN, projection.states().get("financial"));
    assertEquals(SatelliteContractV1.LIST_LOJA_SUBSCRIPTIONS, projection.nextInteraction());
  }

  @Test
  void entitlementPackOnlyIsNotASubscription() {
    ExecutionResult provider =
        new ExecutionResult(
            true,
            "COMPLETED",
            "preq-ent",
            "actionhub-biblioteca",
            null,
            "ACTIONHUB_BIBLIOTECA",
            SatelliteContractV1.WATERMARK_BIBLIOTECA,
            List.of(),
            List.of(),
            Map.of(
                "active",
                false,
                "reason",
                "pack_only",
                "app_id",
                "lojadepaes",
                "entitlement",
                Map.of("pack_credits", 10, "principal_credits", 0)));
    var projection =
        BibliotecaStateProjection.project(
            request("GET_LOJA_ENTITLEMENTS"),
            "READY",
            SatelliteContractV1.GET_HUB_ENTITLEMENTS,
            provider);
    assertEquals("pack_only", projection.states().get("commercial"));
    assertEquals(BibliotecaStateProjection.FINANCIAL_NOT_APPLICABLE, projection.states().get("financial"));
  }

  @Test
  void reserveIdempotentKeepsHubStatus() {
    ExecutionResult provider =
        new ExecutionResult(
            true,
            "COMPLETED",
            "preq-res",
            "actionhub-biblioteca",
            null,
            "ACTIONHUB_BIBLIOTECA",
            SatelliteContractV1.WATERMARK_BIBLIOTECA,
            List.of(),
            List.of(),
            Map.of("ok", true, "status", "reserved", "idempotent", true, "credits", 19));
    var projection =
        BibliotecaStateProjection.project(
            request("RESERVE_LOJA_CREDITS"),
            "READY",
            SatelliteContractV1.RESERVE_HUB_CREDITS,
            provider);
    assertEquals("reserved", projection.states().get("commercial"));
    assertEquals(BibliotecaStateProjection.FINANCIAL_NOT_APPLICABLE, projection.states().get("financial"));
  }

  @Test
  void catalogDoesNotInventFinancialConfirmation() {
    ExecutionResult provider =
        new ExecutionResult(
            true,
            "COMPLETED",
            "preq-cat",
            "actionhub-biblioteca",
            null,
            "ACTIONHUB_BIBLIOTECA",
            SatelliteContractV1.WATERMARK_BIBLIOTECA,
            List.of(),
            List.of(),
            Map.of("app_id", "lojadepaes", "plans", List.of(Map.of("sku", "LOJADEPAES_BIBLIOTECA_MENSAL"))));
    var projection =
        BibliotecaStateProjection.project(
            request("LIST_LOJA_PLANS"), "READY", SatelliteContractV1.LIST_HUB_CATALOG, provider);
    assertEquals(BibliotecaStateProjection.FINANCIAL_NOT_APPLICABLE, projection.states().get("financial"));
    assertEquals("none", projection.states().get("commercial"));
    assertTrue(projection.identities().get("correlationId").toString().startsWith("loja-corr"));
  }

  private static SatelliteInteractionRequest request(String objective) {
    String now = "2026-10-08T22:00:00Z";
    return new SatelliteInteractionRequest(
        "1.5",
        "loja-msg-states-0001",
        "loja-corr-states-0001",
        "lojadepaes",
        "EXPERIENCE",
        "QUERY_STATUS",
        now,
        "idem-states-" + objective,
        SatelliteContractV1.PURPOSE_LOJA_BIBLIOTECA,
        new Objective(objective, "SATELLITE_GOVERNED", now),
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
                Map.of("channel", "LOJADEPAES", "theme", "biblioteca_plans", "appId", "lojadepaes"),
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
        Map.of("biblioteca", Map.of("appId", "lojadepaes")));
  }
}
