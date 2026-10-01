package br.com.banco.spider.integration.outbound.provider;

import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionRequest;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

final class ActionHubPayListIdentity {

  private ActionHubPayListIdentity() {}

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
        && !SatelliteContractV1.LIST_PAYMENT_TRANSACTIONS.equals(String.valueOf(body.get("capabilityId")))) {
      return Map.of();
    }
    Object resultNode = body.get("result");
    if (!(resultNode instanceof Map<?, ?> result)) {
      return Map.of();
    }
    Map<String, Object> inputs = request.capabilityInputs() == null ? Map.of() : request.capabilityInputs();
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
    String expectedEnv = text(inputs.get("environment"));
    String actualEnv = text(result.get("environment"));
    if (expectedEnv != null && actualEnv != null && !expectedEnv.equals(actualEnv)) {
      return Map.of();
    }
    Object rawItems = result.get("items");
    if (!(rawItems instanceof List<?> rawList)) {
      return Map.of();
    }
    List<Map<String, Object>> items = new ArrayList<>();
    for (Object entry : rawList) {
      if (!(entry instanceof Map<?, ?> row)) {
        return Map.of();
      }
      Map<String, Object> item = normalizeItem(row);
      if (item.isEmpty()) {
        return Map.of();
      }
      items.add(item);
    }
    Map<String, Object> quote = new LinkedHashMap<>();
    quote.put("kind", "EXTERNAL_PAYMENT_LIST");
    quote.put("companyId", actualCompany == null ? expectedCompany : actualCompany);
    quote.put("payAppId", actualApp == null ? expectedApp : actualApp);
    quote.put("environment", actualEnv == null ? expectedEnv : actualEnv);
    quote.put("origin", text(result.get("origin")));
    quote.put("testLabeled", Boolean.TRUE.equals(result.get("testLabeled")) || Boolean.TRUE.equals(result.get("sandbox")));
    quote.put("itemCount", items.size());
    quote.put("nextCursor", text(result.get("nextCursor")));
    quote.put("items", items);
    quote.put("automaticSettlement", false);
    quote.put("importPersisted", false);
    return quote;
  }

  private static Map<String, Object> normalizeItem(Map<?, ?> row) {
    String transactionId = text(row.get("transactionId"));
    if (transactionId == null || transactionId.isBlank()) {
      return Map.of();
    }
    Object amountRaw = row.get("amountMinor");
    String amount = ActionHubPayLookupIdentity.amountDigits(amountRaw);
    if (amountRaw != null && amount == null) {
      return Map.of();
    }
    Map<String, Object> item = new LinkedHashMap<>();
    item.put("transactionId", transactionId);
    item.put("orderReference", firstText(row.get("orderReference"), transactionId));
    item.put("processorReference", text(row.get("processorReference")));
    item.put("companyBinding", text(row.get("companyBinding")));
    item.put("origin", firstText(row.get("origin"), "ACTIONHUB_PAY"));
    item.put("environment", text(row.get("environment")));
    item.put("originalStatus", text(row.get("originalStatus")));
    item.put("normalizedStatus", text(row.get("normalizedStatus")));
    item.put("amountMinor", amount);
    item.put("amountAbsent", amount == null || Boolean.TRUE.equals(row.get("amountAbsent")));
    item.put("currency", text(row.get("currency")));
    item.put("createdAt", text(row.get("createdAt")));
    item.put("updatedAt", text(row.get("updatedAt")));
    item.put("originRevision", text(first(row.get("originRevision"), row.get("updatedAt"))));
    item.put("testLabeled", Boolean.TRUE.equals(row.get("testLabeled")));
    item.put("reviewRequired", Boolean.TRUE.equals(row.get("reviewRequired")) || amount == null);
    return item;
  }

  private static Object first(Object left, Object right) {
    return left != null ? left : right;
  }

  private static String firstText(Object left, String fallback) {
    String value = text(left);
    return value == null || value.isBlank() ? fallback : value;
  }

  private static String text(Object value) {
    return value == null ? null : String.valueOf(value);
  }
}
