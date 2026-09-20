package br.com.spiderbank.infrastructure;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.spiderbank.application.GovernedCreditContext;
import br.com.spiderbank.application.SpiderDecisionGateway;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;

class HttpSpiderDecisionAdapterTest {

  @Test
  void blankSecretDoesNotCallSpider() throws Exception {
    HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    AtomicReference<Integer> hits = new AtomicReference<>(0);
    server.createContext("/v1/satellites/interactions", exchange -> {
      hits.set(hits.get() + 1);
      exchange.sendResponseHeaders(500, -1);
      exchange.close();
    });
    server.start();
    try {
      HttpSpiderDecisionAdapter adapter =
          new HttpSpiderDecisionAdapter(
              "http://127.0.0.1:" + server.getAddress().getPort(),
              "spiderbank",
              "",
              Duration.ofSeconds(1),
              Duration.ofSeconds(2),
              8192);
      SpiderDecisionGateway.Result result = adapter.submit(command());
      assertEquals(SpiderDecisionGateway.Kind.SPIDER_UNAVAILABLE, result.kind());
      assertEquals(0, hits.get());
    } finally {
      server.stop(0);
    }
  }

  @Test
  void sendsSatelliteHeadersAndDoesNotCallProviderPorts() throws Exception {
    HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    AtomicReference<String> satelliteId = new AtomicReference<>();
    AtomicReference<String> path = new AtomicReference<>();
    server.createContext("/v1/satellites/interactions", exchange -> {
      satelliteId.set(exchange.getRequestHeaders().getFirst(HttpSpiderDecisionAdapter.SATELLITE_ID_HEADER));
      path.set(exchange.getRequestURI().getPath());
      byte[] body =
          "{\"status\":\"PLAN_IMPEDED\",\"correlationId\":\"corr-http-1\"}".getBytes(StandardCharsets.UTF_8);
      exchange.getResponseHeaders().add("Content-Type", "application/json");
      exchange.sendResponseHeaders(200, body.length);
      exchange.getResponseBody().write(body);
      exchange.close();
    });
    server.start();
    try {
      HttpSpiderDecisionAdapter adapter =
          new HttpSpiderDecisionAdapter(
              "http://127.0.0.1:" + server.getAddress().getPort(),
              "spiderbank",
              "test-secret",
              Duration.ofSeconds(1),
              Duration.ofSeconds(2),
              8192);
      SpiderDecisionGateway.Result result = adapter.submit(command());
      assertEquals(SpiderDecisionGateway.Kind.OK, result.kind());
      assertEquals("spiderbank", satelliteId.get());
      assertEquals("/v1/satellites/interactions", path.get());
      assertTrue(result.body().containsKey("status"));
    } finally {
      server.stop(0);
    }
  }

  @Test
  void timeoutIsTechnicalUnavailability() {
    HttpSpiderDecisionAdapter adapter =
        new HttpSpiderDecisionAdapter(
            "http://127.0.0.1:1",
            "spiderbank",
            "test-secret",
            Duration.ofMillis(200),
            Duration.ofMillis(200),
            8192);
    SpiderDecisionGateway.Result result = adapter.submit(command());
    assertEquals(SpiderDecisionGateway.Kind.SPIDER_UNAVAILABLE, result.kind());
    assertTrue(result.message().contains("não é recusa de crédito"));
  }

  private static SpiderDecisionGateway.Command command() {
    return new SpiderDecisionGateway.Command(
        "corr-http-1",
        "idem-http-1",
        "msg-http-1",
        "2026-09-18T15:00:00Z",
        GovernedCreditContext.attributes());
  }
}
