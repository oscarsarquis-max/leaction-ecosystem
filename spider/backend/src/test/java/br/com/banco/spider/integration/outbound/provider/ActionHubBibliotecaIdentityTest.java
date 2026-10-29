package br.com.banco.spider.integration.outbound.provider;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionRequest;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ActionHubBibliotecaIdentityTest {

  @Test
  void acceptsCompletedAndFailedEnvelopesForLoja() {
    ExecutionRequest request = request(SatelliteContractV1.GET_HUB_ENTITLEMENTS);
    Map<String, Object> ok =
        ActionHubBibliotecaIdentity.validatedResult(
            request,
            Map.of(
                "providerId",
                "actionhub-biblioteca",
                "requestId",
                "preq-1",
                "correlationId",
                "corr-1",
                "capabilityId",
                SatelliteContractV1.GET_HUB_ENTITLEMENTS,
                "status",
                "COMPLETED",
                "result",
                Map.of("app_id", "lojadepaes", "active", true)));
    assertFalse(ok.isEmpty());
    Map<String, Object> denied =
        ActionHubBibliotecaIdentity.validatedResult(
            request,
            Map.of(
                "providerId",
                "actionhub-biblioteca",
                "requestId",
                "preq-1",
                "correlationId",
                "corr-1",
                "capabilityId",
                SatelliteContractV1.GET_HUB_ENTITLEMENTS,
                "status",
                "FAILED",
                "result",
                Map.of("ok", false, "error", "insufficient_credits")));
    assertFalse(denied.isEmpty());
    assertTrue(denied.containsKey("error"));
  }

  @Test
  void rejectsForeignAppAndPayCapability() {
    ExecutionRequest entitlements = request(SatelliteContractV1.GET_HUB_ENTITLEMENTS);
    assertTrue(
        ActionHubBibliotecaIdentity.validatedResult(
                entitlements,
                Map.of(
                    "providerId",
                    "actionhub-biblioteca",
                    "requestId",
                    "preq-1",
                    "correlationId",
                    "corr-1",
                    "capabilityId",
                    SatelliteContractV1.GET_HUB_ENTITLEMENTS,
                    "status",
                    "COMPLETED",
                    "result",
                    Map.of("app_id", "inove4us")))
            .isEmpty());
    ExecutionRequest pay =
        new ExecutionRequest(
            "preq-1",
            "corr-1",
            "spd-1",
            SatelliteContractV1.LOOKUP_ACTIONHUB_PAYMENT,
            SatelliteContractV1.PURPOSE_FINANCIAL_EXTERNAL_LOOKUP,
            "pay",
            "INTERNAL",
            Map.of());
    assertTrue(
        ActionHubBibliotecaIdentity.validatedResult(
                pay,
                Map.of(
                    "providerId",
                    "actionhub-biblioteca",
                    "requestId",
                    "preq-1",
                    "correlationId",
                    "corr-1",
                    "capabilityId",
                    SatelliteContractV1.LOOKUP_ACTIONHUB_PAYMENT,
                    "result",
                    Map.of("app_id", "lojadepaes")))
            .isEmpty());
  }

  private static ExecutionRequest request(String capabilityId) {
    return new ExecutionRequest(
        "preq-1",
        "corr-1",
        "spd-1",
        capabilityId,
        SatelliteContractV1.PURPOSE_LOJA_BIBLIOTECA,
        "biblioteca_plans",
        "INTERNAL",
        Map.of(),
        Map.of("appId", "lojadepaes"));
  }
}
