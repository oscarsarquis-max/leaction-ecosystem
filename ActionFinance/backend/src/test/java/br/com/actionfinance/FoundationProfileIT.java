package br.com.actionfinance;

import br.com.actionfinance.support.PostgresFoundationContainer;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = "spring.profiles.active=")
@AutoConfigureMockMvc
@Testcontainers
class FoundationProfileIT {

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
        registry.add("actionfinance.demo-auth.enabled", () -> "true");
        registry.add("actionfinance.demo-auth.operator-a-token", () -> "operator-demo-token-aaaaaaaaaaaaaaaaaaaa");
        registry.add("actionfinance.cors.allowed-origins", () -> "http://127.0.0.1:5179");
    }

    @Autowired
    MockMvc mockMvc;

    @Test
    void demoFlagWithoutLocalDemoProfileDoesNotAuthenticate() throws Exception {
        mockMvc.perform(
                        get("/api/v1/access/me")
                                .header("Authorization", "Bearer operator-demo-token-aaaaaaaaaaaaaaaaaaaa"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void disallowedOriginIsNotReflected() throws Exception {
        mockMvc.perform(get("/api/v1/system/info").header("Origin", "https://evil.example"))
                .andExpect(status().isForbidden())
                .andExpect(header().doesNotExist("Access-Control-Allow-Origin"));
    }
}
