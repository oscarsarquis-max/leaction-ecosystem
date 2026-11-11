package br.com.banco.spider.operational.observation;

import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventType;
import br.com.banco.spider.operational.monitor.MonitorProjectionPort;
import br.com.banco.spider.operational.monitor.MonitorProjectionService;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;

/** Reconstrói a projeção a partir de um fato já persistido, com o horário original. */
public final class ObservationApplier {

  private final ObjectMapper mapper =
      new ObjectMapper().configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

  public void apply(MonitorProjectionPort port, Instant occurredAt, String payload) {
    try {
      JsonNode node = mapper.readTree(payload);
      SatelliteInteractionRequest request =
          mapper.treeToValue(node.get("request"), SatelliteInteractionRequest.class);
      MonitorProjectionService projection =
          new MonitorProjectionService(port, MonitorProjectionService.DEFAULT_RETENTION, clock(occurredAt));
      String kind = node.path("kind").asText("");
      if ("REPLAY".equals(kind)) {
        projection.recordReplayPassed(request);
        return;
      }
      if ("PAYMENTS".equals(kind)) {
        Map<String, Object> quote = mapper.convertValue(node.get("quote"), Map.class);
        projection.recordDiscoveredPayments(
            request,
            new ExecutionResult(
                node.path("available").asBoolean(false),
                "READY",
                null,
                node.path("providerId").asText(null),
                null,
                "ACTIONHUB_PAY",
                null,
                List.of(),
                List.of(),
                quote));
        return;
      }
      OperationalEventType type = OperationalEventType.valueOf(node.path("eventType").asText());
      OperationalEventOutcome outcome = OperationalEventOutcome.valueOf(text(node, "outcome", "INFO"));
      projection.touchInteraction(request, type, outcome, text(node, "technicalState", null));
    } catch (RuntimeException exception) {
      throw exception;
    } catch (Exception exception) {
      throw new IllegalStateException("Fato observável inválido.", exception);
    }
  }

  private static Clock clock(Instant occurredAt) {
    return Clock.fixed(occurredAt == null ? Instant.EPOCH : occurredAt, ZoneOffset.UTC);
  }

  private static String text(JsonNode node, String field, String fallback) {
    JsonNode value = node.get(field);
    if (value == null || value.isNull() || value.asText().isBlank()) {
      return fallback;
    }
    return value.asText();
  }
}
