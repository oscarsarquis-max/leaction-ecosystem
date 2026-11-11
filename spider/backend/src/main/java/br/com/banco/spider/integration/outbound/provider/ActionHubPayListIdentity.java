package br.com.banco.spider.integration.outbound.provider;

import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionRequest;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Response item revision 2026-10-15. Additive fields on the existing list response.
 * Request envelopes stay 1.3 and 1.4. This revision is not a new contractVersion.
 */
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
    List<Map<String, Object>> reviews = new ArrayList<>();
    Object rawReviews = result.get("reviews");
    if (rawReviews instanceof List<?> rawReviewList) {
      for (Object entry : rawReviewList) {
        if (!(entry instanceof Map<?, ?> row)) {
          continue;
        }
        Map<String, Object> review = normalizeItem(row);
        if (!review.isEmpty()) {
          reviews.add(review);
        }
      }
    }
    quote.put("itemCount", items.size());
    quote.put("reviewCount", reviews.size());
    quote.put("nextCursor", text(result.get("nextCursor")));
    quote.put("items", items);
    quote.put("reviews", reviews);
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
    String paid = ActionHubPayLookupIdentity.amountDigits(row.get("paidAmountMinor"));
    if (paid != null) {
      item.put("paidAmountMinor", paid);
      item.put("paidAmountAbsent", false);
    }
    if (text(row.get("chargedAmountMinor")) != null) {
      item.put("chargedAmountMinor", ActionHubPayLookupIdentity.amountDigits(row.get("chargedAmountMinor")));
    }
    item.put("currency", text(row.get("currency")));
    item.put("createdAt", text(row.get("createdAt")));
    item.put("updatedAt", text(row.get("updatedAt")));
    item.put("originRevision", text(first(row.get("originRevision"), row.get("updatedAt"))));
    item.put("testLabeled", Boolean.TRUE.equals(row.get("testLabeled")));
    item.put("reviewRequired", Boolean.TRUE.equals(row.get("reviewRequired")) || amount == null);
    if (text(row.get("classification")) != null) {
      item.put("classification", text(row.get("classification")));
    }
    if (text(row.get("classificationReason")) != null) {
      item.put("classificationReason", text(row.get("classificationReason")));
    }
    putIfPresent(item, row, "paymentMethod");
    putIfPresent(item, row, "payerKind");
    putIfPresent(item, row, "payerLabel");
    putIfPresent(item, row, "payerProvenance");
    putIfPresent(item, row, "commercialApplication");
    putIfPresent(item, row, "commercialDescription");
    putIfPresent(item, row, "processorName");
    putIfPresent(item, row, "providerStatus");
    putIfPresent(item, row, "channel");
    return item;
  }

  private static void putIfPresent(Map<String, Object> item, Map<?, ?> row, String key) {
    String value = text(row.get(key));
    if (value != null && !value.isBlank() && !"null".equals(value)) {
      item.put(key, value);
    }
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
