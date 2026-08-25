package br.com.banco.spider.integration.inbound.http.console;

import br.com.banco.spider.application.console.OperationalConsoleAction;
import br.com.banco.spider.application.console.OperationalConsoleAuthenticationPort;
import br.com.banco.spider.application.console.OperationalConsoleAuthorizationPort;
import br.com.banco.spider.application.console.OperationalConsoleSecurityContext;
import br.com.banco.spider.operational.capacity.CapacityQueryService;
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

/** Leitura do governo de capacidade pela borda operacional, com autorização real por ação. */
@SpringBootTest
@AutoConfigureWebTestClient
@Import(CapacityHttpEndpointE2ETest.SelectiveConsoleAuth.class)
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
      "spider.worker-runtime.tick-interval=PT10S",
      "spider.worker-runtime.stale-after=PT30S",
      "spider.worker-runtime.instance-id=wrk-inst-capacity",
      "spider.capacity.enabled=true",
      "spider.capacity.http.enabled=true",
      "spider.capacity.enforcement.enabled=true",
      "spring.datasource.url=jdbc:h2:mem:spider_capacity_e2e;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.driver-class-name=org.h2.Driver",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=create-drop",
      "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect"
    })
class CapacityHttpEndpointE2ETest {

  private static final String ALLOWED = "cred:capacity-viewer";
  private static final String DENIED = "cred:no-capacity";

  @Autowired WebTestClient client;
  @Autowired CapacityQueryService queryService;

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
                  || action != OperationalConsoleAction.VIEW_CAPACITY);
    }
  }

  @Test
  void snapshotDeclaresItsBoundaryAndMode() {
    client
        .get()
        .uri("/v1/console/capacity")
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
        .jsonPath("$.mode")
        .isEqualTo("ENFORCED")
        .jsonPath("$.policies.length()")
        .isEqualTo(queryService.policies().size())
        .jsonPath("$.pressure.length()")
        .isEqualTo(queryService.policies().size())
        .jsonPath("$.dataQuality.warnings.length()")
        .exists();
  }

  @Test
  void policiesPressureBulkheadsCircuitsAndDecisionsAreReadable() {
    client
        .get()
        .uri("/v1/console/capacity/policies")
        .header("X-Spider-Credential-Ref", ALLOWED)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.policies[0].code")
        .exists()
        .jsonPath("$.policies[0].scopeType")
        .exists();

    client
        .get()
        .uri("/v1/console/capacity/pressure")
        .header("X-Spider-Credential-Ref", ALLOWED)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.pressure[0].level")
        .exists();

    client
        .get()
        .uri("/v1/console/capacity/bulkheads")
        .header("X-Spider-Credential-Ref", ALLOWED)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.bulkheads")
        .exists();

    client
        .get()
        .uri("/v1/console/capacity/circuits")
        .header("X-Spider-Credential-Ref", ALLOWED)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.circuits")
        .exists();

    client
        .get()
        .uri("/v1/console/capacity/decisions?limit=5")
        .header("X-Spider-Credential-Ref", ALLOWED)
        .exchange()
        .expectStatus()
        .isOk()
        .expectHeader()
        .valueEquals("Cache-Control", "no-store")
        .expectBody()
        .jsonPath("$.decisions")
        .exists();
  }

  @Test
  void deniedActionRespondsNotFoundWithoutEnumeratingScopes() {
    client
        .get()
        .uri("/v1/console/capacity")
        .header("X-Spider-Credential-Ref", DENIED)
        .exchange()
        .expectStatus()
        .isNotFound()
        .expectHeader()
        .valueEquals("Cache-Control", "no-store")
        .expectBody()
        .jsonPath("$.policies")
        .doesNotExist();

    client
        .get()
        .uri("/v1/console/capacity/decisions")
        .header("X-Spider-Credential-Ref", DENIED)
        .exchange()
        .expectStatus()
        .isNotFound()
        .expectBody()
        .jsonPath("$.decisions")
        .doesNotExist();
  }

  @Test
  void operationalHealthGainsCapacityDimensionsWhileTheModuleIsOn() {
    client
        .get()
        .uri("/v1/console/operational-health?window=PT24H")
        .header("X-Spider-Credential-Ref", "cred:health")
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.dimensions[?(@.dimension=='CAPACITY')].status")
        .isEqualTo("HEALTHY")
        .jsonPath("$.dimensions[?(@.dimension=='BACKPRESSURE')].status")
        .exists()
        .jsonPath("$.dimensions[?(@.dimension=='BULKHEAD_SAFETY')].status")
        .isEqualTo("HEALTHY")
        .jsonPath("$.dimensions[?(@.dimension=='CIRCUIT_HEALTH')].status")
        .isEqualTo("HEALTHY");
  }
}
