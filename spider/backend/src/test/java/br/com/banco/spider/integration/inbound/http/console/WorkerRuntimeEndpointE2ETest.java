package br.com.banco.spider.integration.inbound.http.console;

import br.com.banco.spider.application.console.OperationalConsoleAction;
import br.com.banco.spider.application.console.OperationalConsoleAuthenticationPort;
import br.com.banco.spider.application.console.OperationalConsoleAuthorizationPort;
import br.com.banco.spider.application.console.OperationalConsoleSecurityContext;
import br.com.banco.spider.operational.workers.WorkerRuntimeQueryService;
import br.com.banco.spider.operational.workers.WorkerType;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;
import reactor.core.publisher.Mono;

@SpringBootTest
@AutoConfigureWebTestClient
@Import(WorkerRuntimeEndpointE2ETest.SelectiveConsoleAuth.class)
@TestPropertySource(
    properties = {
      "spider.console.enabled=true",
      "spider.console.http.enabled=true",
      "spider.canonical.persistence.mode=memory",
      "spider.canonical.http.enabled=false",
      "spider.telemetry.enabled=true",
      "spider.operational-health.enabled=true",
      "spider.operational-health.minimum-sample-size=1",
      "spider.worker-runtime.enabled=true",
      "spider.worker-runtime.http.enabled=true",
      "spider.worker-runtime.tick-interval=PT10S",
      "spider.worker-runtime.stale-after=PT30S",
      "spider.worker-runtime.instance-id=wrk-inst-e2e",
      "spring.datasource.url=jdbc:h2:mem:spider_runtime_e2e;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.driver-class-name=org.h2.Driver",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=create-drop",
      "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect"
    })
class WorkerRuntimeEndpointE2ETest {

  private static final String ALLOWED = "cred:runtime-viewer";
  private static final String DENIED = "cred:no-runtime";

  @Autowired WebTestClient client;
  @Autowired WorkerRuntimeQueryService queryService;

  /** Autorização real por ação: só o principal habilitado enxerga o runtime. */
  @TestConfiguration
  static class SelectiveConsoleAuth {
    @Bean
    @Primary
    OperationalConsoleAuthenticationPort testAuth() {
      return ref ->
          Mono.just(new OperationalConsoleSecurityContext(ref == null ? "anon" : ref, "TEST", true));
    }

    @Bean
    @Primary
    OperationalConsoleAuthorizationPort testAuthz() {
      return (context, action) ->
          Mono.just(
              ALLOWED.equals(context.principalRef())
                  || action != OperationalConsoleAction.VIEW_WORKER_RUNTIME
                      && action != OperationalConsoleAction.DRAIN_WORKER);
    }
  }

  @Test
  void snapshotIsAvailableWhenRuntimeIsEnabledAndActionIsAuthorized() {
    client
        .get()
        .uri("/v1/console/runtime")
        .header("X-Spider-Credential-Ref", ALLOWED)
        .exchange()
        .expectStatus()
        .isOk()
        .expectHeader()
        .valueEquals("Cache-Control", "no-store")
        .expectBody()
        .jsonPath("$.schemaVersion")
        .isEqualTo(1)
        .jsonPath("$.boundary")
        .isEqualTo("SIMULATED_INFRASTRUCTURE")
        .jsonPath("$.integrationBoundary")
        .isEqualTo("MOCK_ONLY")
        .jsonPath("$.workers.length()")
        .isEqualTo(WorkerType.values().length)
        .jsonPath("$.schedules.length()")
        .isEqualTo(WorkerType.values().length);
  }

  @Test
  void workersScheduleAndBacklogReadsAreAvailable() {
    client
        .get()
        .uri("/v1/console/runtime/workers")
        .header("X-Spider-Credential-Ref", ALLOWED)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.workers.length()")
        .isEqualTo(WorkerType.values().length);

    client
        .get()
        .uri("/v1/console/runtime/schedules")
        .header("X-Spider-Credential-Ref", ALLOWED)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.schedules[0].scheduleCode")
        .exists();

    client
        .get()
        .uri("/v1/console/runtime/backlogs")
        .header("X-Spider-Credential-Ref", ALLOWED)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.backlogs.length()")
        .isEqualTo(WorkerType.values().length);
  }

  @Test
  void knownWorkerIsReadableAndUnknownWorkerIsNotEnumerated() {
    String workerId = queryService.workers().getFirst().workerId();
    client
        .get()
        .uri("/v1/console/runtime/workers/{id}", workerId)
        .header("X-Spider-Credential-Ref", ALLOWED)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.workerId")
        .isEqualTo(workerId);

    client
        .get()
        .uri("/v1/console/runtime/workers/{id}", "wrk-inst-does-not-exist:signal_application")
        .header("X-Spider-Credential-Ref", ALLOWED)
        .exchange()
        .expectStatus()
        .isNotFound();
  }

  @Test
  void deniedActionRespondsNotFoundWithoutRevealingTheRuntime() {
    client
        .get()
        .uri("/v1/console/runtime")
        .header("X-Spider-Credential-Ref", DENIED)
        .exchange()
        .expectStatus()
        .isNotFound()
        .expectHeader()
        .valueEquals("Cache-Control", "no-store");
  }

  @Test
  void operationalHealthGainsRuntimeDimensionsWhileTheRuntimeIsOn() {
    client
        .get()
        .uri("/v1/console/operational-health?window=PT24H")
        .header("X-Spider-Credential-Ref", "cred:health")
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.dimensions[?(@.dimension=='WORKER_RUNTIME')].status")
        .isEqualTo("HEALTHY")
        .jsonPath("$.dimensions[?(@.dimension=='SCHEDULING')].status")
        .exists()
        .jsonPath("$.dimensions[?(@.dimension=='BACKLOG')].status")
        .exists()
        .jsonPath("$.dimensions[?(@.dimension=='LEASE_SAFETY')].status")
        .isEqualTo("HEALTHY");
  }

  @Test
  void drainIsRefusedWhileNotExplicitlyAllowed() {
    String workerId = queryService.workers().getFirst().workerId();
    client
        .post()
        .uri("/v1/console/runtime/workers/{id}/drain", workerId)
        .header("X-Spider-Credential-Ref", ALLOWED)
        .exchange()
        .expectStatus()
        .isNotFound();
  }
}
