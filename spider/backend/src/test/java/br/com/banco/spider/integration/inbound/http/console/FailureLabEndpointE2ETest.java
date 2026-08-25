package br.com.banco.spider.integration.inbound.http.console;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.application.console.OperationalConsoleAuthenticationPort;
import br.com.banco.spider.application.console.OperationalConsoleAuthorizationPort;
import br.com.banco.spider.application.console.OperationalConsoleSecurityContext;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;
import reactor.core.publisher.Mono;

@SpringBootTest
@AutoConfigureWebTestClient(timeout = "PT60S")
@Import(FailureLabEndpointE2ETest.PermissiveConsoleAuth.class)
@TestPropertySource(
    properties = {
      "spider.console.enabled=true",
      "spider.console.http.enabled=true",
      "spider.failure-lab.enabled=true",
      "spider.failure-lab.http.enabled=true",
      "spider.telemetry.enabled=true",
      "spider.operational-health.enabled=true",
      "spider.operational-health.minimum-sample-size=1",
      "spider.adapter.mock.enabled=true",
      "spider.canonical.persistence.mode=memory",
      "spring.datasource.url=jdbc:h2:mem:spider_failure_lab_e2e;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.driver-class-name=org.h2.Driver",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=create-drop"
    })
class FailureLabEndpointE2ETest {

  @Autowired WebTestClient client;

  @Test
  void catalogIsPublishedWithoutCaching() {
    client
        .get()
        .uri("/v1/console/failure-lab/scenarios")
        .exchange()
        .expectStatus()
        .isOk()
        .expectHeader()
        .valueEquals("Cache-Control", "no-store")
        .expectBody()
        .jsonPath("$.schemaVersion")
        .isEqualTo(1)
        .jsonPath("$.boundary")
        .isEqualTo("MOCK_ONLY")
        .jsonPath("$.scenarios[?(@.code=='RETRY_THEN_SUCCESS')].version")
        .isEqualTo("1.0")
        .jsonPath("$.runbooks[0].code")
        .exists();
  }

  @Test
  void retryThenSuccessRunIsVerifiedAgainstCanonicalSources() {
    Map<String, Object> run = startRun("RETRY_THEN_SUCCESS", "1.0");

    assertTrue(
        List.of("VERIFIED", "INCONCLUSIVE").contains(run.get("status")),
        "status inesperado: " + run.get("status"));
    assertEquals("MOCK_ONLY", run.get("boundary"));

    List<String> executionRefs = executionRefs(run);
    assertFalse(executionRefs.isEmpty(), "a execução controlada deve registrar ao menos uma referência");

    Map<String, Object> attempts = observation(run, "AT_LEAST_TWO_ATTEMPTS");
    assertEquals("PASSED", attempts.get("status"), "resultado: " + attempts);

    Map<String, Object> succeeded = observation(run, "EXECUTION_SUCCEEDED");
    assertEquals("PASSED", succeeded.get("status"), "resultado: " + succeeded);

    assertEquals("PASSED", observation(run, "NO_SECRET_EXPOSED").get("status"));
    assertEquals("VERIFIED", run.get("status"));
  }

  @Test
  void insufficientSampleNeverClaimsHealth() {
    Map<String, Object> run = startRun("INSUFFICIENT_SAMPLE", "1.0");

    assertTrue(
        List.of("VERIFIED", "INCONCLUSIVE").contains(run.get("status")),
        "status inesperado: " + run.get("status"));
    assertTrue(executionRefs(run).isEmpty(), "o cenário de amostra não submete execução");

    for (Map<String, Object> result : verificationResults(run)) {
      String observed = String.valueOf(result.get("observed"));
      assertFalse(
          "PASSED".equals(result.get("status")) && observed.contains("HEALTHY"),
          "afirmação indevida de saúde: " + result);
    }
    assertEquals("PASSED", observation(run, "NO_SECRET_EXPOSED").get("status"));
  }

  @Test
  void runAndEvidenceAreRetrievableById() {
    Map<String, Object> started = startRun("RETRY_THEN_SUCCESS", "1.0");
    String labRunId = String.valueOf(started.get("labRunId"));

    Map<String, Object> fetched =
        client
            .get()
            .uri("/v1/console/failure-lab/runs/{id}", labRunId)
            .exchange()
            .expectStatus()
            .isOk()
            .expectHeader()
            .valueEquals("Cache-Control", "no-store")
            .expectBody(new ParameterizedTypeReference<Map<String, Object>>() {})
            .returnResult()
            .getResponseBody();

    assertNotNull(fetched);
    assertEquals(labRunId, fetched.get("labRunId"));
    assertEquals("RETRY_THEN_SUCCESS", fetched.get("scenarioCode"));

    client
        .get()
        .uri("/v1/console/failure-lab/runs/{id}/evidence", labRunId)
        .exchange()
        .expectStatus()
        .isOk()
        .expectHeader()
        .valueEquals("Cache-Control", "no-store")
        .expectBody()
        .jsonPath("$.labRunId")
        .isEqualTo(labRunId)
        .jsonPath("$.boundary")
        .isEqualTo("MOCK_ONLY")
        .jsonPath("$.redactionStatus")
        .isEqualTo("APPLIED")
        .jsonPath("$.digest")
        .isNotEmpty();
  }

  @Test
  void unknownScenarioIsNotDisclosed() {
    client
        .post()
        .uri("/v1/console/failure-lab/runs")
        .bodyValue(Map.of("scenarioCode", "NO_SUCH_SCENARIO", "scenarioVersion", "1.0"))
        .exchange()
        .expectStatus()
        .isNotFound();

    client
        .get()
        .uri("/v1/console/failure-lab/runs/{id}", "labrun-inexistente")
        .exchange()
        .expectStatus()
        .isNotFound();
  }

  @Test
  void scenarioCodeIsMandatory() {
    client
        .post()
        .uri("/v1/console/failure-lab/runs")
        .bodyValue(Map.of("scenarioVersion", "1.0"))
        .exchange()
        .expectStatus()
        .isBadRequest();
  }

  private Map<String, Object> startRun(String scenarioCode, String scenarioVersion) {
    Map<String, Object> body =
        client
            .post()
            .uri("/v1/console/failure-lab/runs")
            .bodyValue(Map.of("scenarioCode", scenarioCode, "scenarioVersion", scenarioVersion))
            .exchange()
            .expectStatus()
            .isAccepted()
            .expectHeader()
            .valueEquals("Cache-Control", "no-store")
            .expectBody(new ParameterizedTypeReference<Map<String, Object>>() {})
            .returnResult()
            .getResponseBody();
    assertNotNull(body, "corpo da resposta ausente");
    return body;
  }

  @SuppressWarnings("unchecked")
  private static List<String> executionRefs(Map<String, Object> run) {
    Object refs = run.get("executionRefs");
    return refs == null ? List.of() : (List<String>) refs;
  }

  @SuppressWarnings("unchecked")
  private static List<Map<String, Object>> verificationResults(Map<String, Object> run) {
    Object results = run.get("verificationResults");
    return results == null ? List.of() : (List<Map<String, Object>>) results;
  }

  private static Map<String, Object> observation(Map<String, Object> run, String code) {
    return verificationResults(run).stream()
        .filter(result -> code.equals(result.get("observationCode")))
        .findFirst()
        .orElseThrow(
            () ->
                new AssertionError(
                    "observação " + code + " ausente em " + verificationResults(run)));
  }

  @TestConfiguration
  static class PermissiveConsoleAuth {
    @Bean
    @Primary
    OperationalConsoleAuthenticationPort authentication() {
      return ref ->
          Mono.just(new OperationalConsoleSecurityContext("failure-lab-test", "TEST", true));
    }

    @Bean
    @Primary
    OperationalConsoleAuthorizationPort authorization() {
      return (context, action) -> Mono.just(true);
    }
  }
}
