package br.com.actionfinance;

import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.application.finance.LocalDemoSeed;
import br.com.actionfinance.support.PostgresFoundationContainer;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("local-demo")
@Testcontainers
class MixedCompanyAuthorizationIT {

    private static final String MIXED = "mixed-ab-demo-token-eeeeeeeeeeeeeeeeee";
    private static final String OPERATOR = "operator-demo-token-aaaaaaaaaaaaaaaaaaaa";

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
        registry.add("actionfinance.demo-auth.mixed-ab-token", () -> MIXED);
        registry.add("actionfinance.clock.zone", () -> "America/Sao_Paulo");
        registry.add("actionfinance.clock.fixed-instant", () -> "2026-09-15T15:00:00Z");
    }

    @Autowired
    MockMvc mockMvc;

    @Autowired
    ObjectMapper mapper;

    @Test
    void mixedRoleReadsBothCompaniesAndWritesOnlyOperatorCompany() throws Exception {
        JsonNode me =
                mapper.readTree(
                        mockMvc.perform(get("/api/v1/access/me").header("Authorization", "Bearer " + MIXED))
                                .andExpect(status().isOk())
                                .andReturn()
                                .getResponse()
                                .getContentAsString());
        assertThat(me.get("permissionsByCompany").get(DemoPrincipalCatalog.COMPANY_A.toString()).toString())
                .contains("titles:write");
        assertThat(me.get("permissionsByCompany").get(DemoPrincipalCatalog.COMPANY_B.toString()).toString())
                .doesNotContain("titles:write");

        mockMvc.perform(
                        get("/api/v1/receivables")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + MIXED))
                .andExpect(status().isOk());
        mockMvc.perform(
                        get("/api/v1/receivables")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_B.toString())
                                .header("Authorization", "Bearer " + MIXED))
                .andExpect(status().isOk());

        String created =
                mockMvc.perform(
                                post("/api/v1/receivables")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .param("register", "true")
                                        .header("Authorization", "Bearer " + MIXED)
                                        .header("Idempotency-Key", UUID.randomUUID().toString())
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content(titleBody(LocalDemoSeed.CP_PADARIA_CLIENTE, LocalDemoSeed.CAT_VENDA)))
                        .andExpect(status().isOk())
                        .andReturn()
                        .getResponse()
                        .getContentAsString();
        JsonNode createdJson = mapper.readTree(created);
        assertThat(createdJson.get("id").asText()).isNotBlank();
        assertThat(createdJson.get("description").asText()).isEqualTo("Titulo misto");

        String refusedKey = "mixed-replay-" + UUID.randomUUID();
        mockMvc.perform(
                        post("/api/v1/receivables")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_B.toString())
                                .param("register", "true")
                                .header("Authorization", "Bearer " + MIXED)
                                .header("Idempotency-Key", refusedKey)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(titleBody(LocalDemoSeed.CP_ATELIE_CLIENTE, LocalDemoSeed.CAT_VENDA_B)))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("FORBIDDEN"));

        mockMvc.perform(
                        post("/api/v1/receivables")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_B.toString())
                                .param("register", "true")
                                .header("Authorization", "Bearer " + MIXED)
                                .header("Idempotency-Key", refusedKey)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(titleBody(LocalDemoSeed.CP_ATELIE_CLIENTE, LocalDemoSeed.CAT_VENDA_B)))
                .andExpect(status().isForbidden());

        mockMvc.perform(
                        post("/api/v1/catalogs/counterparties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_B.toString())
                                .header("Authorization", "Bearer " + MIXED)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"name\":\"Cliente indevido\",\"role\":\"CUSTOMER\"}"))
                .andExpect(status().isForbidden());
        mockMvc.perform(
                        post("/api/v1/financial-accounts")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_B.toString())
                                .header("Authorization", "Bearer " + MIXED)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"name\":\"Caixa B\",\"type\":\"CASH\",\"openedOn\":\"2026-09-01\",\"openingBalanceMinor\":\"0\"}"))
                .andExpect(status().isForbidden());

        JsonNode openB =
                mapper.readTree(
                        mockMvc.perform(
                                        get("/api/v1/receivables")
                                                .param("companyId", DemoPrincipalCatalog.COMPANY_B.toString())
                                                .param("status", "OPEN")
                                                .header("Authorization", "Bearer " + MIXED))
                                .andExpect(status().isOk())
                                .andReturn()
                                .getResponse()
                                .getContentAsString());
        String titleB = openB.get("items").get(0).get("id").asText();
        mockMvc.perform(
                        patch("/api/v1/receivables/" + titleB)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_B.toString())
                                .header("Authorization", "Bearer " + MIXED)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"description\":\"nao\",\"version\":1,\"reason\":\"tentativa indevida\"}"))
                .andExpect(status().isForbidden());
        mockMvc.perform(
                        post("/api/v1/receivables/" + titleB + "/settlements")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_B.toString())
                                .header("Authorization", "Bearer " + MIXED)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"accountId\":\"" + LocalDemoSeed.ACCOUNT_B + "\",\"amountMinor\":\"100\",\"effectiveDate\":\"2026-09-15\",\"method\":\"CASH\",\"version\":1}"))
                .andExpect(status().isForbidden());
    }

    private static String titleBody(UUID counterparty, UUID category) {
        return """
                {
                  "description":"Titulo misto",
                  "counterpartyId":"%s",
                  "categoryId":"%s",
                  "amountMinor":"1000",
                  "currency":"BRL",
                  "competenceDate":"2026-09-15",
                  "dueDate":"2026-09-22"
                }
                """
                .formatted(counterparty, category);
    }
}
