package br.com.banco.spider.integration.inbound.http.console;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;

import br.com.banco.spider.application.console.OperationalConsoleAuthenticationPort;
import br.com.banco.spider.application.console.OperationalConsoleAuthorizationPort;
import br.com.banco.spider.application.console.OperationalConsoleSecurityContext;
import br.com.banco.spider.operational.capacity.BulkheadService;
import br.com.banco.spider.operational.capacity.CapacityAdmissionService;
import br.com.banco.spider.operational.capacity.CapacityPolicyCatalog;
import br.com.banco.spider.operational.capacity.CapacityQueryService;
import br.com.banco.spider.operational.capacity.CircuitBreakerService;
import br.com.banco.spider.operational.capacity.FailureLabCapacityHarness;
import br.com.banco.spider.operational.capacity.QuotaService;
import br.com.banco.spider.operational.health.HealthDimensionCode;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;
import reactor.core.publisher.Mono;

/** Com o governo de capacidade desligado (padrão) nada dele existe nem responde. */
@SpringBootTest
@AutoConfigureWebTestClient
@Import(CapacityEndpointDisabledE2ETest.PermissiveConsoleAuth.class)
@TestPropertySource(
    properties = {
      "spider.console.enabled=true",
      "spider.console.http.enabled=true",
      "spider.canonical.persistence.mode=memory",
      "spider.canonical.http.enabled=false",
      "spider.telemetry.enabled=true",
      "spider.operational-health.enabled=true",
      "spider.operational-health.minimum-sample-size=1",
      "spring.datasource.url=jdbc:h2:mem:spider_capacity_off;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.driver-class-name=org.h2.Driver",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=create-drop",
      "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect"
    })
class CapacityEndpointDisabledE2ETest {

  @Autowired WebTestClient client;
  @Autowired ApplicationContext context;

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

  @Test
  void capacityEndpointServesNoDataWhenFeatureIsOff() {
    client
        .get()
        .uri("/v1/console/capacity")
        .header("X-Spider-Credential-Ref", "cred:any")
        .exchange()
        .expectStatus()
        .value(status -> assertNotEquals(200, status))
        .expectBody()
        .jsonPath("$.policies")
        .doesNotExist()
        .jsonPath("$.pressure")
        .doesNotExist()
        .jsonPath("$.mode")
        .doesNotExist();
  }

  @Test
  void noCapacityBeanIsCreatedWhenFeatureIsOff() {
    assertNoBeanOfType(CapacityQueryService.class);
    assertNoBeanOfType(CapacityAdmissionService.class);
    assertNoBeanOfType(CapacityPolicyCatalog.class);
    assertNoBeanOfType(BulkheadService.class);
    assertNoBeanOfType(CircuitBreakerService.class);
    assertNoBeanOfType(QuotaService.class);
    assertNoBeanOfType(FailureLabCapacityHarness.class);
    assertNoBeanOfType(CapacityHttpController.class);
  }

  @Test
  void operationalHealthKeepsItsDimensionsUnchangedWhileCapacityIsOff() {
    List<String> capacityDimensions =
        List.of(
            HealthDimensionCode.CAPACITY.name(),
            HealthDimensionCode.BACKPRESSURE.name(),
            HealthDimensionCode.BULKHEAD_SAFETY.name(),
            HealthDimensionCode.CIRCUIT_HEALTH.name());
    var body =
        client
            .get()
            .uri("/v1/console/operational-health?window=PT24H")
            .header("X-Spider-Credential-Ref", "cred:health")
            .exchange()
            .expectStatus()
            .isOk()
            .expectBody();
    for (String dimension : capacityDimensions) {
      body.jsonPath("$.dimensions[?(@.dimension=='" + dimension + "')]").doesNotExist();
    }
  }

  private void assertNoBeanOfType(Class<?> type) {
    assertEquals(0, context.getBeanNamesForType(type).length, type.getSimpleName());
  }
}
