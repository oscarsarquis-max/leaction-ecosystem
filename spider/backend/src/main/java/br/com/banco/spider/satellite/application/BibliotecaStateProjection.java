package br.com.banco.spider.satellite.application;

import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import java.net.URI;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * Maps ActionHub Biblioteca results onto separate satellite, technical, commercial and financial
 * states using Hub vocabulary. READY/COMPLETED never means payment confirmed.
 */
public final class BibliotecaStateProjection {

  public static final String MONITOR_COMPANY_ID = "624023a4-57e3-415c-b7d0-925ca1acd3b7";
  public static final String TECHNICAL_COMPLETED = "COMPLETED";
  public static final String TECHNICAL_UNAVAILABLE = "PROVIDER_UNAVAILABLE";
  public static final String TECHNICAL_UNKNOWN = "EFFECT_UNKNOWN";
  public static final String FINANCIAL_NOT_APPLICABLE = "not_applicable";
  public static final String FINANCIAL_PENDING = "pending";
  public static final String FINANCIAL_UNKNOWN = "unknown";
  public static final String FINANCIAL_REFUSED = "refused";
  public static final String COMMERCIAL_NONE = "none";

  private static final Set<String> CHECKOUT_HOSTS =
      Set.of("actionhub.com.br", "www.actionhub.com.br", "localhost", "127.0.0.1");
  private static final Set<String> MUTATING =
      Set.of(
          SatelliteContractV1.START_HUB_CATALOG_CHECKOUT,
          SatelliteContractV1.CANCEL_HUB_SUBSCRIPTION,
          SatelliteContractV1.RESERVE_HUB_CREDITS,
          SatelliteContractV1.CONFIRM_HUB_CREDITS,
          SatelliteContractV1.RELEASE_HUB_CREDITS);

  private BibliotecaStateProjection() {}

  public record Projection(
      Map<String, Object> states,
      Map<String, Object> identities,
      String nextInteraction,
      Map<String, Object> sanitizedSummary) {}

  public static boolean unknownEffect(ExecutionResult provider) {
    if (provider == null || provider.quote() == null) {
      return false;
    }
    return "UNKNOWN".equals(String.valueOf(provider.quote().get("effectCertainty")))
        || "UNKNOWN".equals(provider.status());
  }

  public static boolean mutating(String capabilityId) {
    return MUTATING.contains(capabilityId);
  }

  public static Projection project(
      SatelliteInteractionRequest request,
      String satelliteStatus,
      String capabilityId,
      ExecutionResult provider) {
    Map<String, Object> raw = provider == null || provider.quote() == null ? Map.of() : provider.quote();
    Map<String, Object> summary = sanitize(raw);
    boolean available = provider != null && provider.available();
    boolean unknown = unknownEffect(provider) && mutating(capabilityId);
    String technical =
        available ? TECHNICAL_COMPLETED : unknown ? TECHNICAL_UNKNOWN : TECHNICAL_UNAVAILABLE;
    String commercial = commercialOf(capabilityId, summary, available, unknown);
    String financial = financialOf(capabilityId, summary, available, unknown);
    Map<String, Object> states = new LinkedHashMap<>();
    states.put("satellite", satelliteStatus);
    states.put("technical", technical);
    states.put("commercial", commercial);
    states.put("financial", financial);
    Map<String, Object> identities = identitiesOf(request, provider, summary);
    String next = nextInteractionOf(capabilityId, technical, satelliteStatus);
    return new Projection(states, identities, next, summary.isEmpty() ? null : summary);
  }

  static Map<String, Object> sanitize(Map<String, Object> raw) {
    Map<String, Object> copy = new LinkedHashMap<>();
    raw.forEach(
        (key, value) -> {
          String name = String.valueOf(key).toLowerCase(Locale.ROOT);
          if (name.contains("card")
              || name.contains("token")
              || name.contains("secret")
              || name.contains("password")
              || name.contains("cvv")
              || name.contains("pan")) {
            return;
          }
          if ("checkout_url".equals(name) || "checkouturl".equals(name)) {
            copy.put(key, redactCheckoutUrl(value));
            return;
          }
          if ("email".equals(name) || "subject_id".equals(name) || "subjectid".equals(name)) {
            return;
          }
          copy.put(key, value);
        });
    Object url = copy.get("checkout_url") == null ? copy.get("checkoutUrl") : copy.get("checkout_url");
    if (url != null) {
      copy.put("checkoutHostAllowed", Boolean.valueOf(checkoutHostAllowed(url)));
      if (!checkoutHostAllowed(url)) {
        copy.remove("checkout_url");
        copy.remove("checkoutUrl");
      }
    }
    return copy;
  }

  static boolean checkoutHostAllowed(Object url) {
    String host = hostOf(url);
    return host != null && CHECKOUT_HOSTS.contains(host.toLowerCase(Locale.ROOT));
  }

  static String redactCheckoutUrl(Object url) {
    if (url == null) {
      return null;
    }
    try {
      URI parsed = URI.create(String.valueOf(url));
      if (parsed.getQuery() == null) {
        return parsed.toString();
      }
      StringBuilder query = new StringBuilder();
      for (String part : parsed.getQuery().split("&")) {
        int eq = part.indexOf('=');
        String name = eq < 0 ? part : part.substring(0, eq);
        if ("email".equalsIgnoreCase(name) || "customerEmail".equalsIgnoreCase(name)) {
          continue;
        }
        if (query.length() > 0) {
          query.append('&');
        }
        query.append(part);
      }
      String base = parsed.getScheme() + "://" + parsed.getAuthority() + parsed.getPath();
      return query.length() == 0 ? base : base + "?" + query;
    } catch (RuntimeException ignored) {
      return null;
    }
  }

  private static String hostOf(Object url) {
    try {
      return URI.create(String.valueOf(url)).getHost();
    } catch (RuntimeException ignored) {
      return null;
    }
  }

  private static String commercialOf(
      String capabilityId, Map<String, Object> summary, boolean available, boolean unknown) {
    if (unknown) {
      return "unknown";
    }
    if (!available) {
      return COMMERCIAL_NONE;
    }
    if (truthyFalse(summary.get("ok")) && summary.get("error") != null) {
      return text(summary.get("error"));
    }
    if (SatelliteContractV1.GET_HUB_ENTITLEMENTS.equals(capabilityId)) {
      if (Boolean.TRUE.equals(summary.get("active"))) {
        return "authorized";
      }
      if ("pack_only".equals(text(summary.get("reason")))) {
        return "pack_only";
      }
      String reason = text(summary.get("reason"));
      return reason == null ? COMMERCIAL_NONE : reason;
    }
    if (SatelliteContractV1.LIST_HUB_SUBSCRIPTIONS.equals(capabilityId)) {
      Object items = summary.get("subscriptions");
      if (items instanceof java.util.List<?> list && !list.isEmpty() && list.get(0) instanceof Map<?, ?> first) {
        return text(first.get("status")) == null ? "pending" : text(first.get("status"));
      }
      return COMMERCIAL_NONE;
    }
    if (SatelliteContractV1.START_HUB_CATALOG_CHECKOUT.equals(capabilityId)) {
      return summary.get("checkout_url") != null || summary.get("order_id") != null
          ? "pending"
          : COMMERCIAL_NONE;
    }
    if (SatelliteContractV1.CANCEL_HUB_SUBSCRIPTION.equals(capabilityId)) {
      return text(summary.get("status")) == null ? "cancelled" : text(summary.get("status"));
    }
    if (SatelliteContractV1.RESERVE_HUB_CREDITS.equals(capabilityId)
        || SatelliteContractV1.CONFIRM_HUB_CREDITS.equals(capabilityId)
        || SatelliteContractV1.RELEASE_HUB_CREDITS.equals(capabilityId)) {
      return text(summary.get("status")) == null ? COMMERCIAL_NONE : text(summary.get("status"));
    }
    return COMMERCIAL_NONE;
  }

  private static String financialOf(
      String capabilityId, Map<String, Object> summary, boolean available, boolean unknown) {
    if (SatelliteContractV1.START_HUB_CATALOG_CHECKOUT.equals(capabilityId)) {
      if (unknown) {
        return FINANCIAL_UNKNOWN;
      }
      if (!available) {
        return FINANCIAL_UNKNOWN;
      }
      if (truthyFalse(summary.get("ok"))) {
        return FINANCIAL_REFUSED;
      }
      if (summary.get("checkout_url") != null || summary.get("order_id") != null) {
        return FINANCIAL_PENDING;
      }
      return FINANCIAL_UNKNOWN;
    }
    if (unknown && mutating(capabilityId)) {
      return FINANCIAL_UNKNOWN;
    }
    return FINANCIAL_NOT_APPLICABLE;
  }

  private static String nextInteractionOf(String capabilityId, String technical, String satelliteStatus) {
    if (TECHNICAL_UNKNOWN.equals(technical)
        || "PROVIDER_UNAVAILABLE".equals(satelliteStatus) && mutating(capabilityId)) {
      if (SatelliteContractV1.START_HUB_CATALOG_CHECKOUT.equals(capabilityId)
          || SatelliteContractV1.CANCEL_HUB_SUBSCRIPTION.equals(capabilityId)) {
        return SatelliteContractV1.LIST_LOJA_SUBSCRIPTIONS;
      }
      if (SatelliteContractV1.RESERVE_HUB_CREDITS.equals(capabilityId)
          || SatelliteContractV1.CONFIRM_HUB_CREDITS.equals(capabilityId)
          || SatelliteContractV1.RELEASE_HUB_CREDITS.equals(capabilityId)) {
        return SatelliteContractV1.GET_LOJA_ENTITLEMENTS;
      }
    }
    if (SatelliteContractV1.START_HUB_CATALOG_CHECKOUT.equals(capabilityId)
        && TECHNICAL_COMPLETED.equals(technical)) {
      return SatelliteContractV1.GET_LOJA_ENTITLEMENTS;
    }
    return null;
  }

  private static Map<String, Object> identitiesOf(
      SatelliteInteractionRequest request, ExecutionResult provider, Map<String, Object> summary) {
    Map<String, Object> identities = new LinkedHashMap<>();
    if (request != null) {
      identities.put("messageId", request.messageId());
      identities.put("correlationId", request.correlationId());
      identities.put("idempotencyKey", request.idempotencyKey());
      identities.put("satelliteId", request.satelliteId());
    }
    if (provider != null) {
      identities.put("providerRequestId", provider.requestId());
      identities.put("providerId", provider.providerId());
    }
    putIfPresent(identities, "actionHubOperationId", first(summary, "order_id", "operationId"));
    putIfPresent(identities, "subscriptionId", first(summary, "subscription_id", "id"));
    putIfPresent(identities, "paymentId", first(summary, "payment_id", "paymentId"));
    putIfPresent(identities, "creditReservationId", first(summary, "operation_id", "operationId"));
    Object appId = first(summary, "app_id", "appId");
    if (appId != null) {
      identities.put("appId", appId);
    } else {
      identities.put("appId", "lojadepaes");
    }
    return identities;
  }

  private static Object first(Map<String, Object> summary, String left, String right) {
    if (summary.get(left) != null) {
      return summary.get(left);
    }
    return summary.get(right);
  }

  private static void putIfPresent(Map<String, Object> target, String key, Object value) {
    if (value != null && !String.valueOf(value).isBlank()) {
      target.put(key, value);
    }
  }

  private static boolean truthyFalse(Object value) {
    return Boolean.FALSE.equals(value) || "false".equalsIgnoreCase(String.valueOf(value));
  }

  private static String text(Object value) {
    if (value == null) {
      return null;
    }
    String text = String.valueOf(value).trim();
    return text.isEmpty() || "null".equals(text) ? null : text;
  }
}
