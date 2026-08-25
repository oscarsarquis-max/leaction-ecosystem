package br.com.banco.spider.integration.inbound.http.console;

import br.com.banco.spider.application.console.OperationalConsoleAction;
import br.com.banco.spider.application.console.OperationalConsoleAuthenticationPort;
import br.com.banco.spider.application.console.OperationalConsoleAuthorizationPort;
import br.com.banco.spider.application.console.OperationalConsoleSecurityContext;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.model.ExecutionTransitionRecord;
import br.com.banco.spider.execution.persistence.model.PersistedExecutionPlan;
import br.com.banco.spider.execution.persistence.port.ExecutionControlStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionPlanStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionStepStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionTransitionStorePort;
import br.com.banco.spider.execution.step.AttemptState;
import br.com.banco.spider.execution.step.ExecutionStepRecord;
import br.com.banco.spider.execution.step.StepAttemptRecord;
import br.com.banco.spider.execution.step.StepState;
import br.com.banco.spider.execution.persistence.port.StepAttemptStorePort;
import br.com.banco.spider.operational.events.OperationalEvent;
import br.com.banco.spider.operational.events.OperationalEventCategory;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventStorePort;
import br.com.banco.spider.operational.events.OperationalEventType;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;
import reactor.core.publisher.Mono;

@SpringBootTest
@AutoConfigureWebTestClient
@Import(OperationalConsoleE2EReadModelTest.PermissiveConsoleAuth.class)
@TestPropertySource(
    properties = {
      "spider.console.enabled=true",
      "spider.console.http.enabled=true",
      "spider.console.safe-projections.enabled=true",
      "spider.canonical.persistence.mode=memory",
      "spider.canonical.http.enabled=false",
      "spring.datasource.url=jdbc:h2:mem:spider_console_e2e;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.driver-class-name=org.h2.Driver",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=create-drop",
      "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect"
    })
class OperationalConsoleE2EReadModelTest {

  @Autowired WebTestClient client;
  @Autowired ExecutionControlStorePort controlStore;
  @Autowired ExecutionPlanStorePort planStore;
  @Autowired ExecutionStepStorePort stepStore;
  @Autowired StepAttemptStorePort attemptStore;
  @Autowired ExecutionTransitionStorePort transitionStore;
  @Autowired OperationalEventStorePort operationalEventStore;

  @TestConfiguration
  static class PermissiveConsoleAuth {
    @Bean
    @Primary
    OperationalConsoleAuthenticationPort testAuth() {
      return ref -> Mono.just(new OperationalConsoleSecurityContext("test-op", "TEST", true));
    }

    @Bean
    @Primary
    OperationalConsoleAuthorizationPort testAuthz() {
      return (ctx, action) -> Mono.just(true);
    }
  }

  @BeforeEach
  void seedRetryScenario() {
    Instant now = Instant.parse("2026-08-21T15:00:00Z");
    String id = "e2e-retry-001";
    if (controlStore.findByExecutionId(id).isPresent()) {
      return;
    }
    controlStore.insert(
        new ExecutionControlRecord(
            id,
            "ctx-e2e",
            "corr-e2e-retry-001-full",
            "plan-e2e",
            "RETRY_THEN_SUCCESS",
            "1",
            ExecutionState.SUCCEEDED,
            2,
            TechnicalStatus.SUCCESS,
            now,
            now.plusSeconds(3),
            now.plusSeconds(3),
            null,
            "retention:technical-default@1",
            "owner:test"));
    planStore.insert(
        new PersistedExecutionPlan(
            "plan-e2e",
            id,
            "RETRY_THEN_SUCCESS",
            "1",
            "journey:mock",
            now,
            "integrity:n/a",
            "1.0",
            "{\"ordered\":[\"step-a\"]}"));
    stepStore.insertAll(
        List.of(
            new ExecutionStepRecord(
                id,
                "step-a",
                0,
                StepState.SUCCEEDED,
                1,
                null,
                null,
                null,
                now,
                now.plusSeconds(3),
                now.plusSeconds(3))));
    attemptStore.insert(
        new StepAttemptRecord(
            "att-1",
            id,
            "step-a",
            1,
            "inv-1",
            "binding:mock@1",
            now,
            now.plusSeconds(5),
            now.plusSeconds(1),
            AttemptState.FAILED,
            null,
            "TRANSIENT",
            true,
            "UNCERTAIN",
            List.of()));
    attemptStore.insert(
        new StepAttemptRecord(
            "att-2",
            id,
            "step-a",
            2,
            "inv-2",
            "binding:mock@1",
            now.plusSeconds(1),
            now.plusSeconds(6),
            now.plusSeconds(3),
            AttemptState.SUCCEEDED,
            null,
            null,
            null,
            "CERTAIN",
            List.of()));
    transitionStore.append(
        new ExecutionTransitionRecord(
            "t1", id, 1, ExecutionState.RECEIVED, ExecutionState.RUNNING, "START", now, null));
    transitionStore.append(
        new ExecutionTransitionRecord(
            "t2",
            id,
            2,
            ExecutionState.RUNNING,
            ExecutionState.SUCCEEDED,
            "DONE",
            now.plusSeconds(3),
            null));
    operationalEventStore.append(
        new OperationalEvent(
            "oev-e2e-1",
            1,
            OperationalEventType.EXECUTION_SUCCEEDED,
            OperationalEventCategory.EXECUTION,
            now.plusSeconds(3),
            id,
            null,
            "corr-e2e-retry-001-full",
            "test-seed",
            OperationalEventOutcome.SUCCESS,
            3000L,
            Map.of("routeCode", "RETRY_THEN_SUCCESS")));
  }

  @Test
  void listAndDetailShowPersistedPlanAttemptsTimelineWithoutSecrets() {
    client
        .get()
        .uri("/v1/console/executions?limit=10")
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.items[?(@.executionId=='e2e-retry-001')]")
        .exists();

    client
        .get()
        .uri("/v1/console/executions/e2e-retry-001")
        .exchange()
        .expectStatus()
        .isOk()
        .expectHeader()
        .valueEquals("Cache-Control", "no-store")
        .expectBody()
        .jsonPath("$.plan.available")
        .isEqualTo(true)
        .jsonPath("$.steps.data[0].attemptCount")
        .isEqualTo(2)
        .jsonPath("$.timeline.data[?(@.eventType=='ATTEMPT')]")
        .exists()
        .jsonPath("$.securityPosture.data.dataExposure")
        .isEqualTo("REDACTED")
        .jsonPath("$..token")
        .doesNotExist()
        .jsonPath("$..jwt")
        .doesNotExist()
        .jsonPath("$..ciphertext")
        .doesNotExist();
  }

  @Test
  void operationalEventsEndpointReturnsOrderedNoStoreProjection() {
    client
        .get()
        .uri("/v1/console/executions/e2e-retry-001/events")
        .exchange()
        .expectStatus()
        .isOk()
        .expectHeader()
        .valueEquals("Cache-Control", "no-store")
        .expectBody()
        .jsonPath("$.executionId")
        .isEqualTo("e2e-retry-001")
        .jsonPath("$.items[0].eventType")
        .isEqualTo("EXECUTION_SUCCEEDED")
        .jsonPath("$.items[0].metadata.routeCode")
        .isEqualTo("RETRY_THEN_SUCCESS");
  }

  @Test
  void implementationAndReadinessEndpointsProtectedNoStore() {
    client
        .get()
        .uri("/v1/console/implementation")
        .exchange()
        .expectStatus()
        .isOk()
        .expectHeader()
        .valueEquals("Cache-Control", "no-store")
        .expectBody()
        .jsonPath("$.currentPrompt")
        .isEqualTo("SPIDER-PROMPT-019")
        .jsonPath("$.capabilities.length()")
        .isEqualTo(26)
        .jsonPath("$.mockRealBoundary")
        .isEqualTo("MOCK_ONLY")
        .jsonPath("$..password")
        .doesNotExist()
        .jsonPath("$..secret")
        .doesNotExist();

    client
        .get()
        .uri("/v1/console/presentation/readiness")
        .exchange()
        .expectStatus()
        .isOk()
        .expectHeader()
        .valueEquals("Cache-Control", "no-store")
        .expectBody()
        .jsonPath("$.boundary")
        .isEqualTo("MOCK_ONLY")
        .jsonPath("$.checks")
        .isArray();
  }

  @Test
  void unknownExecutionReturnsNotFoundEquivalent() {
    client
        .get()
        .uri("/v1/console/executions/does-not-exist")
        .exchange()
        .expectStatus()
        .isNotFound();
  }

  @Test
  void legacyOrchestrateStillMapped() {
    // Endpoint exists on app (may reject auth/body) — must not be removed.
    client.post().uri("/v1/products/orchestrate").exchange().expectStatus().value(s -> {
      if (s == 404) {
        throw new AssertionError("legacy endpoint missing");
      }
    });
  }
}
