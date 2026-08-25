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

/** Cenários de capacidade executados pelo laboratório de falhas, ponta a ponta. */
@SpringBootTest
@AutoConfigureWebTestClient(timeout = "PT60S")
@Import(CapacityFailureLabE2ETest.PermissiveConsoleAuth.class)
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
      "spider.worker-runtime.instance-id=wrk-inst-capacity-lab",
      "spider.capacity.enabled=true",
      "spider.capacity.http.enabled=true",
      "spider.capacity.enforcement.enabled=true",
      "spring.datasource.url=jdbc:h2:mem:spider_capacity_lab;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.driver-class-name=org.h2.Driver",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=create-drop"
    })
class CapacityFailureLabE2ETest {

  @Autowired WebTestClient client;

  @Test
  void capacityScenariosArePublishedWithTheirRunbook() {
    client
        .get()
        .uri("/v1/console/failure-lab/scenarios")
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.scenarios[?(@.code=='CAPACITY_BULKHEAD_SATURATION')].category")
        .isEqualTo("CAPACITY_RESILIENCE")
        .jsonPath("$.scenarios[?(@.code=='CAPACITY_CIRCUIT_OPEN_RECOVER')].category")
        .isEqualTo("CAPACITY_RESILIENCE")
        .jsonPath("$.runbooks[?(@.code=='runbook:failure-lab:capacity')].version")
        .isEqualTo("1.0");
  }

  @Test
  void bulkheadSaturationIsRejectedAndTheSlotIsGivenBack() {
    Map<String, Object> run = startRun("CAPACITY_BULKHEAD_SATURATION");

    assertEquals(
        "PASSED", observation(run, "ADMISSION_REJECTED_BY_CAPACITY").get("status"), run.toString());
    assertEquals("PASSED", observation(run, "NO_CONCURRENCY_LEAK").get("status"));
    assertEquals("PASSED", observation(run, "NO_SECRET_EXPOSED").get("status"));
    assertEquals("VERIFIED", run.get("status"));
    assertTrue(
        executionRefs(run).isEmpty(), "cenários de capacidade não submetem execução de negócio");
  }

  @Test
  void circuitOpensRejectsAndClosesAgainAfterASuccessfulProbe() {
    Map<String, Object> run = startRun("CAPACITY_CIRCUIT_OPEN_RECOVER");

    assertEquals(
        "PASSED", observation(run, "CIRCUIT_OPENED_BY_FAILURES").get("status"), run.toString());
    assertEquals("PASSED", observation(run, "ADMISSION_REJECTED_WHILE_OPEN").get("status"));
    assertEquals("PASSED", observation(run, "CIRCUIT_CLOSED_AFTER_PROBE").get("status"));
    assertEquals("VERIFIED", run.get("status"));
  }

  @Test
  void quotaExhaustionIsRejectedUntilTheWindowRolls() {
    Map<String, Object> run = startRun("CAPACITY_QUOTA_EXHAUSTION");

    assertEquals(
        "PASSED", observation(run, "ADMISSION_REJECTED_BY_QUOTA").get("status"), run.toString());
    assertEquals("VERIFIED", run.get("status"));
  }

  @Test
  void loadSheddingHappensBeforeTheClaimAndKeepsTheFencingToken() {
    Map<String, Object> run = startRun("CAPACITY_LOAD_SHEDDING");

    assertEquals(
        "PASSED",
        observation(run, "ADMISSION_REJECTED_BEFORE_CLAIM").get("status"),
        run.toString());
    assertEquals("PASSED", observation(run, "FENCING_TOKEN_PRESERVED").get("status"));
    assertEquals("VERIFIED", run.get("status"));
  }

  @Test
  void backlogHardLimitShedsWhenThePendingQueueIsObservable() {
    Map<String, Object> run = startRun("CAPACITY_BACKLOG_HARD_LIMIT");

    Map<String, Object> shed = observation(run, "LOAD_SHED_ON_HARD_LIMIT");
    assertTrue(
        List.of("PASSED", "INCONCLUSIVE", "NOT_OBSERVED").contains(shed.get("status")),
        "status inesperado: " + shed);
    if (!"PASSED".equals(shed.get("status"))) {
      assertEquals(
          "INCONCLUSIVE",
          run.get("status"),
          "sem fila observável a corrida não pode se declarar verificada");
    } else {
      assertEquals("PASSED", observation(run, "SHED_REASON_IS_BACKLOG").get("status"));
      assertEquals("VERIFIED", run.get("status"));
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
                new AssertionError("observação " + code + " ausente em " + verificationResults(run)));
  }

  @TestConfiguration
  static class PermissiveConsoleAuth {
    @Bean
    @Primary
    OperationalConsoleAuthenticationPort authentication() {
      return ref -> Mono.just(new OperationalConsoleSecurityContext("capacity-lab-test", "TEST", true));
    }

    @Bean
    @Primary
    OperationalConsoleAuthorizationPort authorization() {
      return (context, action) -> Mono.just(true);
    }
  }
}
