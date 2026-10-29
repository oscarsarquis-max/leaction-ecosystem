package br.com.banco.spider.integration.outbound.provider;

import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionRequest;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import java.util.LinkedHashMap;
import java.util.Map;

final class ActionHubBibliotecaIdentity {

  private ActionHubBibliotecaIdentity() {}

  static Map<String, Object> validatedResult(ExecutionRequest request, Map<?, ?> body) {
    if (!HttpActionHubBibliotecaCapabilityAdapter.PROVIDER_ID.equals(body.get("providerId"))) {
      return Map.of();
    }
    if (!request.requestId().equals(String.valueOf(body.get("requestId")))) {
      return Map.of();
    }
    if (!request.correlationId().equals(String.valueOf(body.get("correlationId")))) {
      return Map.of();
    }
    if (!request.capabilityId().equals(String.valueOf(body.get("capabilityId")))) {
      return Map.of();
    }
    if (!SatelliteContractV1.isBibliotecaCapability(request.capabilityId())) {
      return Map.of();
    }
    Object status = body.get("status");
    if (status != null
        && !"COMPLETED".equals(String.valueOf(status))
        && !"FAILED".equals(String.valueOf(status))) {
      return Map.of();
    }
    Object raw = body.get("result");
    if (!(raw instanceof Map<?, ?> result)) {
      return Map.of();
    }
    Map<String, Object> copy = new LinkedHashMap<>();
    result.forEach((key, value) -> copy.put(String.valueOf(key), value));
    Object appId = copy.get("app_id") == null ? copy.get("appId") : copy.get("app_id");
    if (appId != null && !"lojadepaes".equals(String.valueOf(appId)) && copy.get("plans") == null) {
      return Map.of();
    }
    return copy;
  }
}
