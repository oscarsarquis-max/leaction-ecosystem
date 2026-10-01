package br.com.banco.spider.integration.outbound.provider;

import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionRequest;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import java.math.BigDecimal;
import java.util.LinkedHashMap;
import java.util.Map;

final class ActionHubPayLookupIdentity {

  private ActionHubPayLookupIdentity() {}

  static Map<String, Object> validatedQuote(ExecutionRequest request, Map<?, ?> body) {
    if (body == null || !"COMPLETED".equals(body.get("status"))) {
      return Map.of();
    }
    if (!HttpActionHubPayCapabilityAdapter.PROVIDER_ID.equals(body.get("providerId"))) {
      return Map.of();
    }
    if (body.get("requestId") != null && !request.requestId().equals(String.valueOf(body.get("requestId")))) {
      return Map.of();
    }
    if (body.get("correlationId") != null
        && !request.correlationId().equals(String.valueOf(body.get("correlationId")))) {
      return Map.of();
    }
    if (body.get("capabilityId") != null
        && !SatelliteContractV1.LOOKUP_ACTIONHUB_PAYMENT.equals(String.valueOf(body.get("capabilityId")))) {
      return Map.of();
    }
    Object resultNode = body.get("result");
    if (!(resultNode instanceof Map<?, ?> result)) {
      return Map.of();
    }
    Map<String, Object> inputs = request.capabilityInputs() == null ? Map.of() : request.capabilityInputs();
    String expectedRef = text(inputs.get("externalReference"));
    String actualRef = text(result.get("providerReference"));
    if (expectedRef != null && actualRef != null && !expectedRef.equals(actualRef)) {
      return Map.of();
    }
    String expectedCompany = text(inputs.get("companyId"));
    String actualCompany = text(result.get("companyId"));
    if (expectedCompany != null && actualCompany != null && !expectedCompany.equals(actualCompany)) {
      return Map.of();
    }
    String expectedApp = text(inputs.get("payAppId"));
    String actualApp = text(result.get("payAppId"));
    if (expectedApp != null && actualApp != null && !expectedApp.equals(actualApp)) {
      return Map.of();
    }
    Object amountRaw = result.get("amountMinor");
    String amount = amountDigits(amountRaw);
    if (amountRaw != null && amount == null) {
      return Map.of();
    }
    Map<String, Object> quote = new LinkedHashMap<>();
    quote.put("kind", "EXTERNAL_PAYMENT_LOOKUP");
    quote.put("externalStatus", text(result.get("externalStatus")));
    quote.put("deliveryStatus", text(result.get("deliveryStatus")));
    quote.put("amountMinor", amount);
    quote.put("currency", text(result.get("currency")));
    quote.put("providerReference", actualRef);
    quote.put("companyId", actualCompany);
    quote.put("payAppId", actualApp);
    quote.put("sandbox", Boolean.TRUE.equals(result.get("sandbox")));
    quote.put("origin", text(result.get("origin")));
    quote.put("providerObservedAt", text(first(result.get("providerObservedAt"), result.get("observedAt"))));
    quote.put("automaticSettlement", false);
    return quote;
  }

  static String amountDigits(Object raw) {
    if (raw == null) {
      return null;
    }
    if (raw instanceof String text) {
      return validDigits(text.trim());
    }
    if (raw instanceof Integer || raw instanceof Long || raw instanceof Short) {
      return validDigits(String.valueOf(raw));
    }
    if (raw instanceof BigDecimal decimal) {
      if (decimal.scale() > 0 || decimal.signum() <= 0) {
        return null;
      }
      return validDigits(decimal.toPlainString());
    }
    return null;
  }

  private static String validDigits(String value) {
    if (value == null || !value.matches("[0-9]+")) {
      return null;
    }
    if (value.length() > 19) {
      return null;
    }
    return value;
  }

  private static Object first(Object left, Object right) {
    return left != null ? left : right;
  }

  private static String text(Object value) {
    return value == null ? null : String.valueOf(value);
  }
}
