package br.com.banco.spider.satellite.application;

import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import java.time.Instant;
import java.util.Comparator;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Isolated ActionHub → Spider callback contract for Biblioteca. Not a public ingress. External
 * publication remains blocked until Hub emits this event through an authenticated channel.
 */
public final class ActionHubBibliotecaCallbackContract {

  public static final String CONTRACT_VERSION = SatelliteContractV1.VERSION_1_5;
  public static final String EVENT_TYPE = "ACTIONHUB_BIBLIOTECA_STATE";
  public static final String PROVIDER_ID = "actionhub-biblioteca";

  public enum Decision {
    ACCEPT,
    DUPLICATE,
    INVALID,
    OUT_OF_ORDER,
    UNKNOWN_CORRELATION
  }

  public record Evaluation(Decision decision, String reason, boolean resume) {}

  public static final class Store {
    private final ConcurrentHashMap<String, Instant> events = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Instant> latestByCorrelation = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, String> resumedTransitions = new ConcurrentHashMap<>();

    public Evaluation accept(Map<String, Object> event) {
      Evaluation validated = validate(event);
      if (validated.decision() != Decision.ACCEPT) {
        return validated;
      }
      String eventId = text(event.get("callbackEventId"));
      Instant occurredAt = Instant.parse(text(event.get("occurredAt")));
      String correlationId = text(event.get("correlationId"));
      String transition = text(event.get("financialStatus")) + ":" + text(event.get("commercialStatus"));
      Instant previous = events.putIfAbsent(eventId, occurredAt);
      if (previous != null) {
        return new Evaluation(Decision.DUPLICATE, "callbackEventId já persistido", false);
      }
      Instant latest = latestByCorrelation.get(correlationId);
      if (latest != null && occurredAt.isBefore(latest)) {
        return new Evaluation(Decision.OUT_OF_ORDER, "evento anterior ao último aceito", false);
      }
      latestByCorrelation.put(correlationId, occurredAt);
      String resumeKey = correlationId + ":" + transition;
      String already = resumedTransitions.putIfAbsent(resumeKey, eventId);
      boolean resume = already == null;
      return new Evaluation(Decision.ACCEPT, resume ? "retomada única" : "transição já retomada", resume);
    }
  }

  private ActionHubBibliotecaCallbackContract() {}

  public static Evaluation validate(Map<String, Object> event) {
    if (event == null) {
      return new Evaluation(Decision.INVALID, "evento vazio", false);
    }
    if (!CONTRACT_VERSION.equals(text(event.get("contractVersion")))) {
      return new Evaluation(Decision.INVALID, "versão de contrato incompatível", false);
    }
    if (!EVENT_TYPE.equals(text(event.get("eventType")))) {
      return new Evaluation(Decision.INVALID, "tipo de evento desconhecido", false);
    }
    if (!PROVIDER_ID.equals(text(event.get("providerId")))) {
      return new Evaluation(Decision.INVALID, "provedor não autorizado", false);
    }
    if (blank(event.get("callbackEventId"))
        || blank(event.get("correlationId"))
        || blank(event.get("occurredAt"))
        || blank(event.get("capabilityId"))) {
      return new Evaluation(Decision.INVALID, "identidades obrigatórias ausentes", false);
    }
    if (!SatelliteContractV1.isBibliotecaCapability(text(event.get("capabilityId")))) {
      return new Evaluation(Decision.INVALID, "capability fora da Biblioteca", false);
    }
    try {
      Instant.parse(text(event.get("occurredAt")));
    } catch (RuntimeException ignored) {
      return new Evaluation(Decision.INVALID, "occurredAt inválido", false);
    }
    if (containsSensitive(event)) {
      return new Evaluation(Decision.INVALID, "payload contém dado sensível", false);
    }
    if (blank(event.get("correlationId"))) {
      return new Evaluation(Decision.UNKNOWN_CORRELATION, "correlação ausente", false);
    }
    return new Evaluation(Decision.ACCEPT, "contrato válido", false);
  }

  public static Comparator<Map<String, Object>> chronological() {
    return Comparator.comparing(event -> Instant.parse(text(event.get("occurredAt"))));
  }

  private static boolean containsSensitive(Map<String, Object> event) {
    return event.keySet().stream()
        .map(key -> String.valueOf(key).toLowerCase())
        .anyMatch(
            key ->
                key.contains("card")
                    || key.contains("token")
                    || key.contains("secret")
                    || key.contains("cvv")
                    || key.contains("password"));
  }

  private static boolean blank(Object value) {
    return value == null || String.valueOf(value).isBlank();
  }

  private static String text(Object value) {
    return value == null ? "" : String.valueOf(value).trim();
  }
}
