package br.com.actionfinance;

import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.support.PostgresFoundationContainer;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("local-demo")
@Testcontainers
class FoundationSecurityIT {

    private static final String OPERATOR = "operator-demo-token-aaaaaaaaaaaaaaaaaaaa";
    private static final String VIEWER_A = "viewer-a-demo-token-bbbbbbbbbbbbbbbbbbbb";
    private static final String VIEWER_B = "viewer-b-demo-token-cccccccccccccccccccc";

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
        registry.add("server.address", () -> "127.0.0.1");
        registry.add("actionfinance.demo-auth.enabled", () -> "true");
        registry.add("actionfinance.demo-auth.operator-a-token", () -> OPERATOR);
        registry.add("actionfinance.demo-auth.viewer-a-token", () -> VIEWER_A);
        registry.add("actionfinance.demo-auth.viewer-b-token", () -> VIEWER_B);
        registry.add("actionfinance.cors.allowed-origins", () -> "http://127.0.0.1:5179");
    }

    @Autowired
    MockMvc mockMvc;

    @Test
    void publicInfoDoesNotRequireToken() throws Exception {
        mockMvc.perform(get("/api/v1/system/info"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.stage").value("FOUNDATION"))
                .andExpect(jsonPath("$.financialOperationsAvailable").value(true))
                .andExpect(jsonPath("$.spiderIntegrationStatus").value("NOT_IMPLEMENTED"))
                .andExpect(jsonPath("$.accessMode").value("DEMO"));
    }

    @Test
    void missingOrInvalidTokenIsUnauthorized() throws Exception {
        mockMvc.perform(get("/api/v1/access/me")).andExpect(status().isUnauthorized());
        mockMvc.perform(get("/api/v1/access/me").header("Authorization", "Bearer wrong-token-xxxxxxxxxxxxxxxxxxxx"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void validPrincipalSeesOwnProfileAndClientHeadersDoNotEscalate() throws Exception {
        mockMvc.perform(
                        get("/api/v1/access/me")
                                .header("Authorization", "Bearer " + VIEWER_A)
                                .header("X-Actor-Id", DemoPrincipalCatalog.OPERATOR_A)
                                .header("X-Company-Id", DemoPrincipalCatalog.COMPANY_B)
                                .header("X-Role", "operator")
                                .header("X-Permissions", "payments:approve"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.actorId").value(DemoPrincipalCatalog.VIEWER_A.toString()));
    }

    @Test
    void companyBIsForbiddenToCompanyAViewer() throws Exception {
        mockMvc.perform(
                        get("/api/v1/access/context")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_B.toString())
                                .header("Authorization", "Bearer " + VIEWER_A))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.message").value("Não foi possível atender esta consulta."));
    }

    @Test
    void operatorCanReadOwnCompanyContext() throws Exception {
        mockMvc.perform(
                        get("/api/v1/access/context")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.companyId").value(DemoPrincipalCatalog.COMPANY_A.toString()));
    }

    @Test
    void invalidCompanyIdIsBadRequest() throws Exception {
        mockMvc.perform(
                        get("/api/v1/access/context")
                                .param("companyId", "not-a-uuid")
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isBadRequest());
    }

    @Test
    @WithMockUser(authorities = "system:read")
    void contextRequiresCompanyContextPermission() throws Exception {
        mockMvc.perform(
                        get("/api/v1/access/context")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString()))
                .andExpect(status().isForbidden());
    }

    @Test
    void unknownAndFutureRoutesAreDenied() throws Exception {
        mockMvc.perform(get("/api/v1/settlements")).andExpect(status().isUnauthorized());
        mockMvc.perform(get("/api/v1/settlements").header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isForbidden());
        mockMvc.perform(post("/api/v1/access/me").header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isForbidden());
        mockMvc.perform(get("/error").header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isForbidden());
    }

    @Test
    void actuatorInternalsAreHidden() throws Exception {
        mockMvc.perform(get("/actuator/env")).andExpect(status().isUnauthorized());
        mockMvc.perform(get("/actuator/mappings").header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isForbidden());
    }
}
