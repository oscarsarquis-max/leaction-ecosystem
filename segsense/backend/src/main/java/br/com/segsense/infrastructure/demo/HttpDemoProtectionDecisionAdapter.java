package br.com.segsense.infrastructure.demo;

import br.com.segsense.application.demo.CanonicalJourneyMapper;
import br.com.segsense.application.demo.DemoProjectionJson;
import br.com.segsense.application.demo.DemoProtectionDecisionGateway;
import br.com.segsense.application.demo.GovernedDemoOrigin;
import br.com.segsense.domain.demo.DemoProtectionException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

@Component
@Profile({"local", "test"})
@ConditionalOnProperty(name = "segsense.demo.protection-journey.enabled", havingValue = "true")
public class HttpDemoProtectionDecisionAdapter implements DemoProtectionDecisionGateway {

  static final String SATELLITE_ID_HEADER = "X-Spider-Satellite-Id";
  static final String SECRET_HEADER = "X-Spider-Satellite-Secret";

  private final HttpClient http;
  private final URI endpoint;
  private final String satelliteId;
  private final String applicationSecret;

  public HttpDemoProtectionDecisionAdapter(
      @Value("${segsense.demo.spider.base-url}") String baseUrl,
      @Value("${segsense.demo.spider.satellite-id:segsense}") String satelliteId,
      @Value("${segsense.demo.spider.application-secret:}") String applicationSecret) {
    this.satelliteId = satelliteId;
    this.applicationSecret = applicationSecret == null ? "" : applicationSecret;
    this.http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build();
    String normalized = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
    this.endpoint = URI.create(normalized + "/v1/satellites/interactions");
  }

  @Override
  public Result submit(Command command) {
    if (applicationSecret.isBlank()) {
      return Result.spiderUnavailable();
    }
    Map<String, Object> provenance = new LinkedHashMap<>();
    provenance.put("sourceType", "SATELLITE_GOVERNED");
    provenance.put("sourceId", GovernedDemoOrigin.EDITORIAL_PIECE_KEY);
    provenance.put("sourceTimestamp", GovernedDemoOrigin.CAPTURED_AT);
    provenance.put("captureMethod", "SERVER_REGISTRY");
    provenance.put("trustLevel", "GOVERNED");
    Map<String, Object> snapshot = new LinkedHashMap<>();
    snapshot.put("schemaVersion", "1.0");
    snapshot.put("classification", "INTERNAL");
    snapshot.put("nonPersonal", true);
    snapshot.put("provenance", provenance);
    snapshot.put(
        "attributes",
        Map.of(
            "channel", GovernedDemoOrigin.CHANNEL,
            "editorialPieceVersion", GovernedDemoOrigin.EDITORIAL_PIECE_VERSION,
            "purposeVersion", GovernedDemoOrigin.PURPOSE_VERSION));
    Map<String, Object> payload = new LinkedHashMap<>();
    payload.put("contractVersion", "1.0");
    payload.put("messageId", "msg-" + UUID.randomUUID());
    payload.put("correlationId", command.correlationId());
    payload.put("satelliteId", satelliteId);
    payload.put("satelliteRole", "EXPERIENCE");
    payload.put("interactionType", "REQUEST_DECISION");
    payload.put("createdAt", GovernedDemoOrigin.CAPTURED_AT);
    payload.put("idempotencyKey", command.idempotencyKey());
    payload.put("purpose", "INSURANCE_PROTECTION_ASSESSMENT");
    payload.put(
        "objective",
        Map.of(
            "text", command.declaredObjective(),
            "origin", "SATELLITE_GOVERNED",
            "declaredAt", GovernedDemoOrigin.CAPTURED_AT));
    payload.put("context", Map.of("snapshot", snapshot));
    payload.put("dataClassification", "INTERNAL");
    payload.put("responseChannel", "SYNC");
    payload.put("metadata", Map.of());
    HttpRequest request =
        HttpRequest.newBuilder(endpoint)
            .timeout(Duration.ofSeconds(5))
            .header("Content-Type", "application/json")
            .header("Accept", "application/json")
            .header(SATELLITE_ID_HEADER, satelliteId)
            .header(SECRET_HEADER, applicationSecret)
            .header("X-Correlation-ID", command.correlationId())
            .header("Idempotency-Key", command.idempotencyKey())
            .POST(HttpRequest.BodyPublishers.ofString(DemoProjectionJson.write(payload)))
            .build();
    try {
      HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
      int status = response.statusCode();
      if (status == 400) {
        throw new DemoProtectionException(
            "VALIDATION_ERROR", 400, "O contexto sintético não foi aceito pela Spider.");
      }
      if (status == 409) {
        throw new DemoProtectionException(
            "IDEMPOTENCY_CONFLICT", 409, "A mesma chave já foi usada com outro pedido.");
      }
      if (status != 200) {
        return Result.spiderUnavailable();
      }
      return CanonicalJourneyMapper.fromSatelliteResponse(DemoProjectionJson.readObject(response.body()));
    } catch (DemoProtectionException validation) {
      throw validation;
    } catch (InterruptedException interrupted) {
      Thread.currentThread().interrupt();
      return Result.spiderUnavailable();
    } catch (Exception ignored) {
      return Result.spiderUnavailable();
    }
  }
}
