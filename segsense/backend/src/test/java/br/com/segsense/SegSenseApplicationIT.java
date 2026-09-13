package br.com.segsense;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import br.com.segsense.inbound.http.security.SecurityFixtureConfiguration;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.client.RestClient;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
@Import(SecurityFixtureConfiguration.class)
@Testcontainers
@ActiveProfiles("test")
class SegSenseApplicationIT {

  @Container
  @ServiceConnection
  static PostgreSQLContainer postgres = new PostgreSQLContainer("postgres:18.6");

  @LocalServerPort int port;

  @Autowired MockMvc mockMvc;

  @Test
  void appliesMigrationsAndExposesTechnicalEndpoints() {
    RestClient client = RestClient.builder().baseUrl("http://127.0.0.1:" + port).build();

    String info =
        client
            .get()
            .uri("/api/v1/system/info")
            .accept(MediaType.APPLICATION_JSON)
            .retrieve()
            .body(String.class);
    assertThat(info).contains("SegSense");
    assertThat(info).contains("0.1.0");
    assertThat(info).contains("\"applicationId\":\"SEGSENSE\"");
    assertThat(info).contains("UP");

    String health = client.get().uri("/actuator/health").retrieve().body(String.class);
    assertThat(health).contains("UP");

    String readiness =
        client.get().uri("/actuator/health/readiness").retrieve().body(String.class);
    assertThat(readiness).contains("UP");
  }

  @Test
  void preservesValidCorrelationIdOnPublicAndDeniedApiRoutes() throws Exception {
    String correlationId = "22222222-2222-2222-2222-222222222222";
    HttpClient http = HttpClient.newHttpClient();

    HttpResponse<String> info =
        http.send(
            HttpRequest.newBuilder(URI.create(baseUrl() + "/api/v1/system/info"))
                .header("X-Correlation-ID", correlationId)
                .GET()
                .build(),
            HttpResponse.BodyHandlers.ofString());
    assertThat(info.statusCode()).isEqualTo(200);
    assertThat(info.headers().firstValue("X-Correlation-ID")).contains(correlationId);

    HttpResponse<String> denied =
        http.send(
            HttpRequest.newBuilder(URI.create(baseUrl() + "/api/v1/does-not-exist"))
                .header("X-Correlation-ID", correlationId)
                .GET()
                .build(),
            HttpResponse.BodyHandlers.ofString());
    assertThat(denied.statusCode()).isEqualTo(401);
    assertThat(denied.headers().firstValue("X-Correlation-ID")).contains(correlationId);
    assertThat(denied.body()).contains("\"code\":\"AUTHENTICATION_REQUIRED\"");
    assertThat(denied.body()).contains("\"correlationId\":\"" + correlationId + "\"");
    assertThat(denied.body())
        .doesNotContain("Exception", "SQL", "stackTrace", "javax.sql", "password", "ROLE_");
    assertThat(denied.headers().firstValue("WWW-Authenticate").orElse(""))
        .doesNotContainIgnoringCase("Basic");
  }

  @Test
  void generatesCorrelationIdWhenHeaderIsAbsentOrInvalid() throws Exception {
    HttpClient http = HttpClient.newHttpClient();

    HttpResponse<String> absent =
        http.send(
            HttpRequest.newBuilder(URI.create(baseUrl() + "/api/v1/system/info")).GET().build(),
            HttpResponse.BodyHandlers.ofString());
    String generated = absent.headers().firstValue("X-Correlation-ID").orElseThrow();
    assertThat(generated)
        .matches("[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}");

    HttpResponse<String> invalid =
        http.send(
            HttpRequest.newBuilder(URI.create(baseUrl() + "/api/v1/system/info"))
                .header("X-Correlation-ID", "not-a-uuid")
                .GET()
                .build(),
            HttpResponse.BodyHandlers.ofString());
    String replaced = invalid.headers().firstValue("X-Correlation-ID").orElseThrow();
    assertThat(replaced).isNotEqualTo("not-a-uuid");
    assertThat(replaced)
        .matches("[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}");
  }

  @Test
  void allowsConfiguredOriginAndCorrelationHeader() throws Exception {
    HttpClient http = HttpClient.newHttpClient();
    HttpResponse<Void> preflight =
        http.send(
            HttpRequest.newBuilder(URI.create(baseUrl() + "/api/v1/system/info"))
                .method("OPTIONS", HttpRequest.BodyPublishers.noBody())
                .header("Origin", "http://127.0.0.1:5178")
                .header("Access-Control-Request-Method", "GET")
                .header("Access-Control-Request-Headers", "X-Correlation-ID")
                .build(),
            HttpResponse.BodyHandlers.discarding());

    assertThat(preflight.statusCode()).isBetween(200, 204);
    assertThat(preflight.headers().firstValue("Access-Control-Allow-Origin"))
        .contains("http://127.0.0.1:5178");
    assertThat(
            preflight.headers().firstValue("Access-Control-Allow-Headers").orElse("").toLowerCase())
        .contains("x-correlation-id");

    HttpResponse<Void> localhostPreflight =
        http.send(
            HttpRequest.newBuilder(URI.create(baseUrl() + "/api/v1/system/info"))
                .method("OPTIONS", HttpRequest.BodyPublishers.noBody())
                .header("Origin", "http://localhost:5178")
                .header("Access-Control-Request-Method", "GET")
                .header("Access-Control-Request-Headers", "X-Correlation-ID")
                .build(),
            HttpResponse.BodyHandlers.discarding());
    assertThat(localhostPreflight.statusCode()).isBetween(200, 204);
    assertThat(localhostPreflight.headers().firstValue("Access-Control-Allow-Origin"))
        .contains("http://localhost:5178");
  }

  @Test
  void anonymousProtectedFixtureReturns401WithMatchingCorrelation() throws Exception {
    String correlationId = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee";
    mockMvc
        .perform(
            get("/api/v1/system/security-fixture/protected")
                .header("X-Correlation-ID", correlationId)
                .header("X-User-Id", "attacker")
                .header("X-Subject-Id", "attacker"))
        .andExpect(status().isUnauthorized())
        .andExpect(header().string("X-Correlation-ID", correlationId))
        .andExpect(header().doesNotExist("WWW-Authenticate"))
        .andExpect(jsonPath("$.code").value("AUTHENTICATION_REQUIRED"))
        .andExpect(jsonPath("$.message").value("Autenticação necessária."))
        .andExpect(jsonPath("$.timestamp").exists())
        .andExpect(jsonPath("$.correlationId").value(correlationId));
  }

  @Test
  void authenticatedFixtureWithoutPolicyReturns403WithMatchingCorrelation() throws Exception {
    String correlationId = "bbbbbbbb-cccc-4ddd-8eee-ffffffffffff";
    mockMvc
        .perform(
            get("/api/v1/system/security-fixture/protected")
                .with(user("tester"))
                .header("X-Correlation-ID", correlationId))
        .andExpect(status().isForbidden())
        .andExpect(header().string("X-Correlation-ID", correlationId))
        .andExpect(jsonPath("$.code").value("ACCESS_DENIED"))
        .andExpect(jsonPath("$.message").value("Acesso não autorizado para esta operação."))
        .andExpect(jsonPath("$.timestamp").exists())
        .andExpect(jsonPath("$.correlationId").value(correlationId));
  }

  @Test
  void doesNotOfferFormLoginOrBasicAuth() throws Exception {
    mockMvc
        .perform(get("/login").accept(MediaType.TEXT_HTML))
        .andExpect(status().isUnauthorized())
        .andExpect(header().doesNotExist("WWW-Authenticate"))
        .andExpect(jsonPath("$.code").value("AUTHENTICATION_REQUIRED"));

    HttpResponse<String> env =
        HttpClient.newHttpClient()
            .send(
                HttpRequest.newBuilder(URI.create(baseUrl() + "/actuator/env")).GET().build(),
                HttpResponse.BodyHandlers.ofString());
    assertThat(env.statusCode()).isIn(401, 403, 404);
    assertThat(env.body()).doesNotContain("propertySources", "systemEnvironment");
    assertThat(env.headers().firstValue("WWW-Authenticate").orElse("")).doesNotContainIgnoringCase("Basic");
    assertThat(env.body()).doesNotContain("<form", "login");
  }

  private String baseUrl() {
    return "http://127.0.0.1:" + port;
  }
}
