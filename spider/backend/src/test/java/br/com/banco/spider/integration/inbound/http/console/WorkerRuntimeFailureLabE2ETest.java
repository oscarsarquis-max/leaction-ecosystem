package br.com.banco.spider.integration.inbound.http.console;

import static org.junit.jupiter.api.Assertions.assertEquals;
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

/** Cenários do runtime de workers executados pelo laboratório de falhas, ponta a ponta. */
@SpringBootTest
@AutoConfigureWebTestClient(timeout = "PT60S")
@Import(WorkerRuntimeFailureLabE2ETest.PermissiveConsoleAuth.class)
@TestPropertySource(
    properties = {
      "spider.console.enabled=true",
      "spider.console.http.enabled=true",
      "spider.failure-lab.enabled=true",
      "spider.failure-lab.http.enabled=true",
      "spider.telemetry.enabled=true",
      "spider.adapter.mock.enabled=true",
      "spider.canonical.persistence.mode=memory",
      "spider.worker-runtime.enabled=true",
      "spider.worker-runtime.tick-interval=PT10S",
      "spider.worker-runtime.stale-after=PT30S",
      "spider.worker-runtime.instance-id=wrk-inst-lab",
      "spring.datasource.url=jdbc:h2:mem:spider_runtime_lab;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.driver-class-name=org.h2.Driver",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=create-drop"
    })
class WorkerRuntimeFailureLabE2ETest {

  @Autowired WebTestClient client;

  @Test
  void workerScenariosArePublishedInTheCatalog() {
    client
        .get()
        .uri("/v1/console/failure-lab/scenarios")
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.scenarios[?(@.code=='WORKER_CRASH_AFTER_CLAIM')].category")
        .isEqualTo("WORKER_RUNTIME")
        .jsonPath("$.runbooks[?(@.code=='runbook:failure-lab:worker-runtime')].version")
        .isEqualTo("1.0");
  }

  @Test
  void crashAfterClaimIsVerifiedWithLeaseExpiryAndFencing() {
    Map<String, Object> run = startRun("WORKER_CRASH_AFTER_CLAIM");

    assertEquals("PASSED", observation(run, "CLAIM_ACQUIRED").get("status"), run.toString());
    assertEquals("PASSED", observation(run, "LEASE_EXPIRED_BY_TIME").get("status"));
    assertEquals("PASSED", observation(run, "RECLAIMED_BY_SECOND_WORKER").get("status"));
    assertEquals("PASSED", observation(run, "STALE_COMPLETION_REJECTED").get("status"));
    assertEquals("PASSED", observation(run, "NO_SECRET_EXPOSED").get("status"));
    assertEquals("VERIFIED", run.get("status"));
    assertTrue(
        executionRefs(run).isEmpty(), "cenários de runtime não submetem execução de negócio");
  }

  @Test
  void dualContentionHasASingleWinner() {
    Map<String, Object> run = startRun("WORKER_DUAL_CONTENTION");
    assertEquals("PASSED", observation(run, "SINGLE_WINNER").get("status"), run.toString());
    assertEquals("VERIFIED", run.get("status"));
  }

  @Test
  void gracefulDrainStopsNewClaims() {
    Map<String, Object> run = startRun("WORKER_GRACEFUL_DRAIN");
    assertEquals("PASSED", observation(run, "WORKER_DRAINING").get("status"), run.toString());
    assertEquals("PASSED", observation(run, "NO_NEW_CLAIMS").get("status"));
    assertEquals("VERIFIED", run.get("status"));
  }

  @Test
  void restartRecoveryKeepsScheduleState() {
    Map<String, Object> run = startRun("WORKER_RESTART_RECOVERY");
    assertEquals(
        "PASSED", observation(run, "SCHEDULE_STATE_SURVIVED").get("status"), run.toString());
    assertEquals("VERIFIED", run.get("status"));
  }

  @Test
  void backlogScenarioNeverClaimsAccumulationWithoutObservingIt() {
    Map<String, Object> run = startRun("WORKER_BACKLOG_ACCUMULATION");

    assertEquals(
        "PASSED",
        observation(run, "BACKLOG_READ_FROM_CANONICAL_SOURCES").get("status"),
        run.toString());
    Map<String, Object> accumulating = observation(run, "BACKLOG_ACCUMULATING");
    assertTrue(
        List.of("PASSED", "INCONCLUSIVE", "NOT_OBSERVED").contains(accumulating.get("status")),
        "status inesperado: " + accumulating);
    if (!"PASSED".equals(accumulating.get("status"))) {
      assertEquals(
          "INCONCLUSIVE",
          run.get("status"),
          "sem fila observada a corrida não pode se declarar verificada");
    }
  }

  private Map<String, Object> startRun(String scenarioCode) {
    Map<String, Object> body =
        client
            .post()
            .uri("/v1/console/failure-lab/runs")
            .bodyValue(Map.of("scenarioCode", scenarioCode, "scenarioVersion", "1.0"))
            .exchange()
            .expectStatus()
            .isAccepted()
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
          Mono.just(new OperationalConsoleSecurityContext("worker-lab-test", "TEST", true));
    }

    @Bean
    @Primary
    OperationalConsoleAuthorizationPort authorization() {
      return (context, action) -> Mono.just(true);
    }
  }
}
