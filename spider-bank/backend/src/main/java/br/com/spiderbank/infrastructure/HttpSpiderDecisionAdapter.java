package br.com.spiderbank.infrastructure;

import br.com.spiderbank.application.SatelliteEnvelopeFactory;
import br.com.spiderbank.application.SatelliteJson;
import br.com.spiderbank.application.SpiderDecisionGateway;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class HttpSpiderDecisionAdapter implements SpiderDecisionGateway {

  static final String SATELLITE_ID_HEADER = "X-Spider-Satellite-Id";
  static final String SECRET_HEADER = "X-Spider-Satellite-Secret";

  private final HttpClient http;
  private final URI endpoint;
  private final String satelliteId;
  private final String applicationSecret;
  private final Duration readTimeout;
  private final int maxBytes;

  public HttpSpiderDecisionAdapter(
      @Value("${spiderbank.spider.base-url}") String baseUrl,
      @Value("${spiderbank.spider.satellite-id}") String satelliteId,
      @Value("${spiderbank.spider.application-secret:}") String applicationSecret,
      @Value("${spiderbank.spider.connect-timeout}") Duration connectTimeout,
      @Value("${spiderbank.spider.read-timeout}") Duration readTimeout,
      @Value("${spiderbank.spider.max-bytes}") int maxBytes) {
    this.satelliteId = satelliteId;
    this.applicationSecret = applicationSecret == null ? "" : applicationSecret;
    this.readTimeout = readTimeout;
    this.maxBytes = maxBytes;
    this.http = HttpClient.newBuilder().connectTimeout(connectTimeout).build();
    String normalized = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
    this.endpoint = URI.create(normalized + "/v1/satellites/interactions");
  }

  @Override
  public Result submit(Command command) {
    if (applicationSecret.isBlank()) {
      return Result.spiderUnavailable();
    }
    try {
      String payload = SatelliteJson.write(SatelliteEnvelopeFactory.build(command));
      if (payload.length() > maxBytes) {
        return Result.integrationFailure("O envelope SAT-003 excedeu o limite configurado.");
      }
      HttpRequest request =
          HttpRequest.newBuilder(endpoint)
              .timeout(readTimeout)
              .header("Content-Type", "application/json")
              .header("Accept", "application/json")
              .header(SATELLITE_ID_HEADER, satelliteId)
              .header(SECRET_HEADER, applicationSecret)
              .header("X-Correlation-ID", command.correlationId())
              .header("Idempotency-Key", command.idempotencyKey())
              .POST(HttpRequest.BodyPublishers.ofString(payload))
              .build();
      HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
      return interpret(response, command.correlationId());
    } catch (InterruptedException interrupted) {
      Thread.currentThread().interrupt();
      return Result.spiderUnavailable();
    } catch (Exception ignored) {
      return Result.spiderUnavailable();
    }
  }

  private Result interpret(HttpResponse<String> response, String correlationId) {
    int status = response.statusCode();
    String raw = response.body() == null ? "" : response.body();
    if (raw.length() > maxBytes) {
      return Result.integrationFailure("A resposta da Spider excedeu o limite configurado.");
    }
    if (status == 401 || status == 403) {
      return new Result(Kind.CLIENT_ERROR, status, "UNAUTHORIZED_SATELLITE", "A credencial do satélite foi recusada.", Map.of());
    }
    if (status == 409) {
      return new Result(Kind.CLIENT_ERROR, 409, "IDEMPOTENCY_CONFLICT", "A mesma chave já foi usada com outro pedido.", Map.of());
    }
    if (status == 400) {
      Map<String, Object> error = readObject(raw);
      String code = string(error.get("errorCode"), "VALIDATION_ERROR");
      String message = string(error.get("message"), "O contexto sintético não foi aceito pela Spider.");
      return new Result(Kind.CLIENT_ERROR, 400, code, message, error);
    }
    if (status != 200) {
      return Result.spiderUnavailable();
    }
    Map<String, Object> body = readObject(raw);
    if (body.isEmpty()) {
      return Result.integrationFailure("A Spider devolveu HTTP 200 sem corpo utilizável.");
    }
    Object returned = body.get("correlationId");
    if (returned != null && !correlationId.equals(String.valueOf(returned))) {
      return Result.integrationFailure("A correlação devolvida pela Spider diverge da enviada.");
    }
    return Result.ok(body);
  }

  private Map<String, Object> readObject(String raw) {
    if (raw == null || raw.isBlank()) {
      return Map.of();
    }
    try {
      return SatelliteJson.readObject(raw);
    } catch (Exception ignored) {
      return Map.of();
    }
  }

  private static String string(Object value, String fallback) {
    return value == null || String.valueOf(value).isBlank() ? fallback : String.valueOf(value);
  }
}
