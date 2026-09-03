package br.com.banco.spider.integration.inbound.http.context;

import static org.junit.jupiter.api.Assertions.assertNotEquals;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.reactive.server.WebTestClient;

@SpringBootTest(properties = "spider.context.enabled=false")
@AutoConfigureWebTestClient
@ActiveProfiles("local-demo")
class ContextIntelligenceDisabledTest {

  @Autowired WebTestClient client;

  @Test
  void contextHttpSurfaceDoesNotExistWhenFlagIsOff() {
    client
        .get()
        .uri("/v1/context/intents")
        .exchange()
        .expectStatus()
        .value(status -> assertNotEquals(200, status))
        .expectBody()
        .jsonPath("$.items")
        .doesNotExist();
  }
}
