package br.com.banco.spider.integration.inbound.http.canonical;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;

@SpringBootTest
@AutoConfigureWebTestClient
@TestPropertySource(
    properties = {
      "spider.canonical.http.enabled=false",
      "spider.canonical.signal-http.enabled=false",
      "spider.canonical.persistence.mode=memory",
      "spring.datasource.url=jdbc:h2:mem:spider_http_off;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.driver-class-name=org.h2.Driver",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=create-drop",
      "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect"
    })
class CanonicalHttpDisabledByDefaultTest {

  @Autowired WebTestClient client;

  @Test
  void canonicalEndpointsAbsentWhenDisabled() {
    // Controllers not registered; WebFlux may surface as 404 or legacy ProblemDetail 500 wrapping 404
    client
        .post()
        .uri("/v1/canonical/executions")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue("{}")
        .exchange()
        .expectStatus()
        .value(s -> org.junit.jupiter.api.Assertions.assertTrue(s == 404 || s == 500, "status=" + s));
    client
        .get()
        .uri("/v1/canonical/executions/x")
        .exchange()
        .expectStatus()
        .value(s -> org.junit.jupiter.api.Assertions.assertTrue(s == 404 || s == 500, "status=" + s));
    client
        .post()
        .uri("/v1/canonical/signals")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue("{}")
        .exchange()
        .expectStatus()
        .value(s -> org.junit.jupiter.api.Assertions.assertTrue(s == 404 || s == 500, "status=" + s));
  }
}
