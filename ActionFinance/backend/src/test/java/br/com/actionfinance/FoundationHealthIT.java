package br.com.actionfinance;

import br.com.actionfinance.support.PostgresFoundationContainer;
import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestMethodOrder;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Testcontainers
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class FoundationHealthIT {

    @Container
    static final PostgreSQLContainer<?> POSTGRES = PostgresFoundationContainer.create();

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", () -> "actionfinance_runtime");
        registry.add("spring.datasource.password", () -> "runtime-test");
        registry.add("spring.flyway.user", () -> "actionfinance_migrator");
        registry.add("spring.flyway.password", () -> "migrator-test");
        registry.add("spring.flyway.url", POSTGRES::getJdbcUrl);
        registry.add("actionfinance.demo-auth.enabled", () -> "false");
        registry.add("server.address", () -> "127.0.0.1");
    }

    @LocalServerPort
    int port;

    @Autowired
    TestRestTemplate restTemplate;

    @Test
    @Order(1)
    void readyWhenOwnDatabaseIsUp() {
        ResponseEntity<String> ready = restTemplate.getForEntity(url("/actuator/health/readiness"), String.class);
        ResponseEntity<String> live = restTemplate.getForEntity(url("/actuator/health/liveness"), String.class);
        assertThat(ready.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(live.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(ready.getBody()).doesNotContain("jdbc:");
    }

    @Test
    @Order(2)
    void readinessFailsAndLivenessStaysUpWhenOwnDatabaseStops() {
        POSTGRES.stop();
        ResponseEntity<String> ready = restTemplate.getForEntity(url("/actuator/health/readiness"), String.class);
        ResponseEntity<String> live = restTemplate.getForEntity(url("/actuator/health/liveness"), String.class);
        assertThat(ready.getStatusCode().is5xxServerError()).isTrue();
        assertThat(live.getStatusCode()).isEqualTo(HttpStatus.OK);
    }

    private String url(String path) {
        return "http://127.0.0.1:" + port + path;
    }
}
