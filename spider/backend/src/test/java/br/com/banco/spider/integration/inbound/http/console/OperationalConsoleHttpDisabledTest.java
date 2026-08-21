package br.com.banco.spider.integration.inbound.http.console;

import static org.junit.jupiter.api.Assertions.assertThrows;

import br.com.banco.spider.config.OperationalConsoleConfig;
import br.com.banco.spider.config.OperationalConsoleProperties;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.core.env.StandardEnvironment;
import org.springframework.mock.env.MockEnvironment;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;
import org.springframework.beans.factory.annotation.Autowired;

@SpringBootTest
@AutoConfigureWebTestClient
@TestPropertySource(
    properties = {
      "spider.console.enabled=false",
      "spider.console.http.enabled=false",
      "spider.canonical.persistence.mode=memory",
      "spring.datasource.url=jdbc:h2:mem:spider_console_off;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.driver-class-name=org.h2.Driver",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=create-drop",
      "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect"
    })
class OperationalConsoleHttpDisabledTest {

  @Autowired WebTestClient client;

  @Test
  void consoleEndpointsAbsentWhenDisabled() {
    client
        .get()
        .uri("/v1/console/executions")
        .exchange()
        .expectStatus()
        .value(s -> org.junit.jupiter.api.Assertions.assertTrue(s == 404 || s == 500, "status=" + s));
  }
}

class OperationalConsoleFlagMatrixTest {

  @Test
  void httpEnabledWithoutConsoleFails() {
    OperationalConsoleProperties props = new OperationalConsoleProperties();
    props.setEnabled(false);
    props.getHttp().setEnabled(true);
    assertThrows(
        IllegalStateException.class,
        () -> new OperationalConsoleConfig(props, new StandardEnvironment()));
  }

  @Test
  void localDemoWithoutProfileFails() {
    OperationalConsoleProperties props = new OperationalConsoleProperties();
    props.setEnabled(true);
    props.getLocalDemo().setEnabled(true);
    MockEnvironment env = new MockEnvironment();
    assertThrows(IllegalStateException.class, () -> new OperationalConsoleConfig(props, env));
  }
}
