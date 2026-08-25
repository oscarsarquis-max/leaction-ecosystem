package br.com.banco.spider.integration.inbound.http.console;

import br.com.banco.spider.application.console.OperationalConsoleAuthenticationPort;
import br.com.banco.spider.application.console.OperationalConsoleAuthorizationPort;
import br.com.banco.spider.application.console.OperationalConsoleSecurityContext;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.port.ExecutionControlStorePort;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.events.OperationalEvent;
import br.com.banco.spider.operational.events.OperationalEventCategory;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventStorePort;
import br.com.banco.spider.operational.events.OperationalEventType;
import java.time.Instant;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
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
@Import(OperationalHealthEndpointE2ETest.PermissiveAuth.class)
@TestPropertySource(
    properties = {
      "spider.console.enabled=true",
      "spider.console.http.enabled=true",
      "spider.telemetry.enabled=true",
      "spider.operational-health.enabled=true",
      "spider.operational-health.minimum-sample-size=1",
      "spider.canonical.persistence.mode=memory",
      "spring.datasource.url=jdbc:h2:mem:spider_health_e2e;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.driver-class-name=org.h2.Driver",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=create-drop"
    })
class OperationalHealthEndpointE2ETest {
  @Autowired WebTestClient client;
  @Autowired ExecutionControlStorePort controls;
  @Autowired OperationalEventStorePort events;
  @Autowired SpiderClock clock;

  @BeforeEach
  void seedExecutionAndEvent() {
    Instant now = clock.now();
    if (controls.findByExecutionId("health-e2e").isEmpty()) {
      controls.insert(
          new ExecutionControlRecord(
              "health-e2e",
              "ctx-health",
              "corr-health",
              "plan",
              "HEALTH_ROUTE",
              "1",
              ExecutionState.SUCCEEDED,
              1,
              TechnicalStatus.SUCCESS,
              now.minusMillis(100),
              now,
              now,
              null,
              "retention:test",
              null));
      events.append(
          new OperationalEvent(
              "event-health-e2e",
              1,
              OperationalEventType.EXECUTION_SUCCEEDED,
              OperationalEventCategory.EXECUTION,
              now,
              "health-e2e",
              null,
              "corr-health",
              "test",
              OperationalEventOutcome.SUCCESS,
              100L,
              Map.of()));
    }
  }

  @Test
  void returnsProvisionalMockOnlyHealthFromStores() {
    client
        .get()
        .uri("/v1/console/operational-health?window=PT24H")
        .exchange()
        .expectStatus()
        .isOk()
        .expectHeader()
        .valueEquals("Cache-Control", "no-store")
        .expectBody()
        .jsonPath("$.schemaVersion")
        .isEqualTo(1)
        .jsonPath("$.integrationLevel")
        .isEqualTo("MOCK_ONLY")
        .jsonPath("$.provisional")
        .isEqualTo(true)
        .jsonPath("$.slis[0].code")
        .isEqualTo("EXECUTION_TECHNICAL_RELIABILITY")
        .jsonPath("$.slis[0].value")
        .isEqualTo(1.0);
  }

  @TestConfiguration
  static class PermissiveAuth {
    @Bean
    @Primary
    OperationalConsoleAuthenticationPort authentication() {
      return ref -> Mono.just(new OperationalConsoleSecurityContext("health-test", "TEST", true));
    }

    @Bean
    @Primary
    OperationalConsoleAuthorizationPort authorization() {
      return (context, action) -> Mono.just(true);
    }
  }
}
