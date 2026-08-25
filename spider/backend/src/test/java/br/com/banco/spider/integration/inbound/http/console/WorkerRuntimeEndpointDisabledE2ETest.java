package br.com.banco.spider.integration.inbound.http.console;

import br.com.banco.spider.application.console.OperationalConsoleAuthenticationPort;
import br.com.banco.spider.application.console.OperationalConsoleAuthorizationPort;
import br.com.banco.spider.application.console.OperationalConsoleSecurityContext;
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

/** Com o runtime desligado (padrão) a borda operacional não expõe nem existe. */
@SpringBootTest
@AutoConfigureWebTestClient
@Import(WorkerRuntimeEndpointDisabledE2ETest.PermissiveConsoleAuth.class)
@TestPropertySource(
    properties = {
      "spider.console.enabled=true",
      "spider.console.http.enabled=true",
      "spider.canonical.persistence.mode=memory",
      "spider.canonical.http.enabled=false",
      "spring.datasource.url=jdbc:h2:mem:spider_runtime_off;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.driver-class-name=org.h2.Driver",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=create-drop",
      "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect"
    })
class WorkerRuntimeEndpointDisabledE2ETest {

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
  void runtimeEndpointServesNoDataWhenFeatureIsOff() {
    // A rota não existe no contexto: qualquer resposta é de erro e nunca traz leitura do runtime.
    client
        .get()
        .uri("/v1/console/runtime")
        .header("X-Spider-Credential-Ref", "cred:any")
        .exchange()
        .expectStatus()
        .value(status -> org.junit.jupiter.api.Assertions.assertNotEquals(200, status))
        .expectBody()
        .jsonPath("$.workers")
        .doesNotExist()
        .jsonPath("$.schedules")
        .doesNotExist()
        .jsonPath("$.runtimeStatus")
        .doesNotExist();
  }

  @Test
  void noWorkerRuntimeBeanIsCreatedWhenFeatureIsOff() {
    assertNoBeanOfType(br.com.banco.spider.operational.workers.WorkerRuntimeCoordinator.class);
    assertNoBeanOfType(br.com.banco.spider.operational.workers.WorkerRuntimeQueryService.class);
    assertNoBeanOfType(br.com.banco.spider.operational.workers.WorkerBacklogQueryService.class);
    assertNoBeanOfType(br.com.banco.spider.operational.workers.RequestWorkerDrainUseCase.class);
    assertNoBeanOfType(br.com.banco.spider.operational.workers.WorkerInstanceStorePort.class);
    assertNoBeanOfType(br.com.banco.spider.operational.workers.DurableScheduleStorePort.class);
    assertNoBeanOfType(br.com.banco.spider.operational.workers.FailureLabWorkerHarness.class);
  }

  private void assertNoBeanOfType(Class<?> type) {
    org.junit.jupiter.api.Assertions.assertEquals(
        0, context.getBeanNamesForType(type).length, type.getSimpleName());
  }
}
