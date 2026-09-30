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
import org.springframework.test.web.servlet.MvcResult;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

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
class TitleOperationsIT {

    private static final String OPERATOR = "operator-demo-token-aaaaaaaaaaaaaaaaaaaa";
    private static final String VIEWER_A = "viewer-a-demo-token-bbbbbbbbbbbbbbbbbbbb";
    private static final String VIEWER_B = "viewer-b-demo-token-cccccccccccccccccccc";
    private static final String MULTI = "operator-multi-token-dddddddddddddddddd";

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
        registry.add("actionfinance.demo-auth.operator-multi-token", () -> MULTI);
        registry.add("actionfinance.clock.zone", () -> "America/Sao_Paulo");
        registry.add("actionfinance.clock.fixed-instant", () -> "2026-09-15T15:00:00Z");
    }

    @Autowired
    MockMvc mockMvc;

    @Autowired
    ObjectMapper mapper;

    @Test
    void listsAndSummarizesBeyondFirstPageWithoutCancelledOrDrafts() throws Exception {
        mockMvc.perform(
                        get("/api/v1/receivables")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("status", "CANCELLED")
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.summary.openCount").value(0))
                .andExpect(jsonPath("$.summary.overdueCount").value(0))
                .andExpect(jsonPath("$.summary.draftCount").value(0));
        mockMvc.perform(
                        get("/api/v1/receivables")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("status", "ALL")
                                .param("q", "Rascunho de recebível demonstrativo")
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.summary.openCount").value(0))
                .andExpect(jsonPath("$.summary.draftCount").value(1))
                .andExpect(jsonPath("$.businessDate").value("2026-09-15"));
        mockMvc.perform(
                        get("/api/v1/receivables")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("status", "OPEN")
                                .param("overdueOnly", "true")
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.summary.overdueCount").value(1))
                .andExpect(jsonPath("$.items[0].overdue").value(true));

        mockMvc.perform(
                        get("/api/v1/receivables/" + LocalDemoSeed.TITLE_REC_OVERDUE)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.overdue").value(true));

        mockMvc.perform(
                        get("/api/v1/receivables/" + LocalDemoSeed.TITLE_REC_TODAY)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.overdue").value(false));
    }

    @Test
    void registersCorrectsAndCancelsBothDirections() throws Exception {
        String rec = createRegistered("/api/v1/receivables", LocalDemoSeed.CP_PADARIA_CLIENTE, LocalDemoSeed.CAT_VENDA, "Recebível de teste");
        JsonNode recJson = mapper.readTree(rec);
        mockMvc.perform(
                        patch("/api/v1/receivables/" + recJson.get("id").asText())
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("""
                                        {
                                          "description":"Recebível corrigido",
                                          "counterpartyId":"%s",
                                          "categoryId":"%s",
                                          "amountMinor":"1500",
                                          "currency":"BRL",
                                          "competenceDate":"2026-09-15",
                                          "dueDate":"2026-09-20",
                                          "version":%d,
                                          "reason":"Ajuste de valor demonstrativo"
                                        }
                                        """
                                        .formatted(
                                                LocalDemoSeed.CP_PADARIA_CLIENTE,
                                                LocalDemoSeed.CAT_VENDA,
                                                recJson.get("version").asLong())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.description").value("Recebível corrigido"));

        mockMvc.perform(
                        get("/api/v1/receivables/" + recJson.get("id").asText() + "/history")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items[0].action").value("UPDATED"));

        String pag = createRegistered("/api/v1/payables", LocalDemoSeed.CP_PADARIA_FORNECEDOR, LocalDemoSeed.CAT_INSUMOS, "Conta a pagar de teste");
        JsonNode pagJson = mapper.readTree(pag);
        mockMvc.perform(
                        post("/api/v1/payables/" + pagJson.get("id").asText() + "/cancel")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"version\":%d,\"reason\":\"Cancelamento de teste\"}".formatted(pagJson.get("version").asLong())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("CANCELLED"));
    }

    @Test
    void isolatesCompaniesAndRejectsCrossTenantReferences() throws Exception {
        mockMvc.perform(
                        get("/api/v1/receivables/" + LocalDemoSeed.TITLE_ATELIE_REC)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.message").value("Não foi possível atender esta consulta."));

        mockMvc.perform(
                        post("/api/v1/receivables")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("register", "true")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("""
                                        {
                                          "description":"Tentativa cruzada",
                                          "counterpartyId":"%s",
                                          "categoryId":"%s",
                                          "amountMinor":"1000",
                                          "currency":"BRL",
                                          "competenceDate":"2026-09-15",
                                          "dueDate":"2026-09-16"
                                        }
                                        """
                                        .formatted(LocalDemoSeed.CP_ATELIE_CLIENTE, LocalDemoSeed.CAT_VENDA)))
                .andExpect(status().isBadRequest());

        mockMvc.perform(
                        get("/api/v1/receivables")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_C.toString())
                                .header("Authorization", "Bearer " + MULTI))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items[0].description").value("Consulta demonstrativa"));
    }

    @Test
    void readerCannotWriteAndOperatorCannotForgeActor() throws Exception {
        mockMvc.perform(
                        post("/api/v1/receivables")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + VIEWER_A)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"description\":\"Não deve gravar\"}"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.message").value("Você não tem permissão para esta ação."));

        mockMvc.perform(
                        get("/api/v1/receivables")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + VIEWER_B))
                .andExpect(status().isForbidden());
    }

    @Test
    void rejectsInvalidMoneyAndReplaysIdempotency() throws Exception {
        mockMvc.perform(
                        post("/api/v1/receivables")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("register", "true")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("""
                                        {
                                          "description":"Valor inválido",
                                          "counterpartyId":"%s",
                                          "categoryId":"%s",
                                          "amountMinor":"12.50",
                                          "currency":"BRL",
                                          "competenceDate":"2026-09-15",
                                          "dueDate":"2026-09-16"
                                        }
                                        """
                                        .formatted(LocalDemoSeed.CP_PADARIA_CLIENTE, LocalDemoSeed.CAT_VENDA)))
                .andExpect(status().isBadRequest());

        String key = "idem-" + UUID.randomUUID();
        String body =
                """
                {
                  "description":"Idempotente",
                  "counterpartyId":"%s",
                  "categoryId":"%s",
                  "amountMinor":"2500",
                  "currency":"BRL",
                  "competenceDate":"2026-09-15",
                  "dueDate":"2026-09-18"
                }
                """
                        .formatted(LocalDemoSeed.CP_PADARIA_CLIENTE, LocalDemoSeed.CAT_VENDA);
        MvcResult first = mockMvc.perform(
                        post("/api/v1/receivables")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("register", "true")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", key)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(body))
                .andExpect(status().isOk())
                .andReturn();
        String id = mapper.readTree(first.getResponse().getContentAsString()).get("id").asText();
        mockMvc.perform(
                        post("/api/v1/receivables")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("register", "true")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", key)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(id));
        mockMvc.perform(
                        post("/api/v1/receivables")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("register", "true")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", key)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(body.replace("2500", "2600")))
                .andExpect(status().isConflict());
    }

    @Test
    void concurrentIdempotentCreatesReturnTheSameTitle() throws Exception {
        String key = "conc-" + UUID.randomUUID();
        String body =
                """
                {
                  "description":"Concorrente",
                  "counterpartyId":"%s",
                  "categoryId":"%s",
                  "amountMinor":"3333",
                  "currency":"BRL",
                  "competenceDate":"2026-09-15",
                  "dueDate":"2026-09-19"
                }
                """
                        .formatted(LocalDemoSeed.CP_PADARIA_CLIENTE, LocalDemoSeed.CAT_VENDA);
        CountDownLatch start = new CountDownLatch(1);
        AtomicInteger oks = new AtomicInteger();
        var pool = Executors.newFixedThreadPool(2);
        Future<String> left = pool.submit(() -> performCreate(start, key, body, oks));
        Future<String> right = pool.submit(() -> performCreate(start, key, body, oks));
        start.countDown();
        String a = left.get(20, TimeUnit.SECONDS);
        String b = right.get(20, TimeUnit.SECONDS);
        pool.shutdownNow();
        assertThat(oks.get()).isEqualTo(2);
        assertThat(mapper.readTree(a).get("id").asText()).isEqualTo(mapper.readTree(b).get("id").asText());
    }

    @Test
    void sameIdempotencyKeyOnDifferentTitleConflicts() throws Exception {
        String first = createDraft("Primeiro rascunho");
        String second = createDraft("Segundo rascunho");
        JsonNode a = mapper.readTree(first);
        JsonNode b = mapper.readTree(second);
        String key = "shared-" + UUID.randomUUID();
        String body = updateBody("Corpo compartilhado", a.get("version").asLong());
        mockMvc.perform(
                        patch("/api/v1/receivables/" + a.get("id").asText())
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", key)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(a.get("id").asText()));
        mockMvc.perform(
                        patch("/api/v1/receivables/" + b.get("id").asText())
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", key)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(updateBody("Corpo compartilhado", b.get("version").asLong())))
                .andExpect(status().isConflict());
        mockMvc.perform(
                        get("/api/v1/receivables/" + b.get("id").asText())
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.description").value("Segundo rascunho"))
                .andExpect(jsonPath("$.status").value("DRAFT"));
    }

    @Test
    void replayKeepsOriginalSuccessAfterLaterChange() throws Exception {
        String created = createDraft("Rascunho para replay");
        JsonNode json = mapper.readTree(created);
        String id = json.get("id").asText();
        String key = "replay-" + UUID.randomUUID();
        mockMvc.perform(
                        patch("/api/v1/receivables/" + id)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", key)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(updateBody("Primeira edição", json.get("version").asLong())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.description").value("Primeira edição"))
                .andExpect(jsonPath("$.version").value(2));
        mockMvc.perform(
                        patch("/api/v1/receivables/" + id)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(updateBody("Segunda edição", 2)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.description").value("Segunda edição"));
        mockMvc.perform(
                        patch("/api/v1/receivables/" + id)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", key)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(updateBody("Primeira edição", json.get("version").asLong())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.description").value("Primeira edição"))
                .andExpect(jsonPath("$.version").value(2));
        mockMvc.perform(
                        get("/api/v1/receivables/" + id + "/history")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items.length()").value(3));
    }

    @Test
    void registerDraftOnEditBecomesOpenAtomically() throws Exception {
        String created = createDraft("Rascunho incompleto");
        JsonNode json = mapper.readTree(created);
        String id = json.get("id").asText();
        mockMvc.perform(
                        patch("/api/v1/receivables/" + id)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("register", "true")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(
                                        """
                                        {
                                          "description":"Rascunho completo",
                                          "counterpartyId":"%s",
                                          "categoryId":"%s",
                                          "amountMinor":"4400",
                                          "currency":"BRL",
                                          "competenceDate":"2026-09-15",
                                          "dueDate":"2026-09-20",
                                          "version":%s
                                        }
                                        """
                                                .formatted(
                                                        LocalDemoSeed.CP_PADARIA_CLIENTE,
                                                        LocalDemoSeed.CAT_VENDA,
                                                        json.get("version").asLong())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("OPEN"))
                .andExpect(jsonPath("$.description").value("Rascunho completo"));
        mockMvc.perform(
                        get("/api/v1/receivables/" + id + "/history")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items[0].action").value("CONFIRMED"));
    }

    @Test
    void listSnapshotStaysInternallyConsistentUnderConcurrentUpdate() throws Exception {
        String created = createRegistered(
                "/api/v1/receivables",
                LocalDemoSeed.CP_PADARIA_CLIENTE,
                LocalDemoSeed.CAT_VENDA,
                "Snapshot");
        JsonNode json = mapper.readTree(created);
        CountDownLatch start = new CountDownLatch(1);
        var pool = Executors.newFixedThreadPool(2);
        Future<String> listed = pool.submit(
                () -> {
                    start.await(5, TimeUnit.SECONDS);
                    return mockMvc.perform(
                                    get("/api/v1/receivables")
                                            .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                            .param("status", "OPEN")
                                            .param("size", "50")
                                            .header("Authorization", "Bearer " + OPERATOR))
                            .andReturn()
                            .getResponse()
                            .getContentAsString();
                });
        Future<Integer> updated = pool.submit(
                () -> {
                    start.await(5, TimeUnit.SECONDS);
                    return mockMvc.perform(
                                    patch("/api/v1/receivables/" + json.get("id").asText())
                                            .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                            .header("Authorization", "Bearer " + OPERATOR)
                                            .header("Idempotency-Key", UUID.randomUUID().toString())
                                            .contentType(MediaType.APPLICATION_JSON)
                                            .content(
                                                    updateBody("Snapshot atualizado", json.get("version").asLong())
                                                            .replace("1000", "7777")
                                                            .replace("\"reason\":null", "\"reason\":\"Ajuste concorrente\"")))
                            .andReturn()
                            .getResponse()
                            .getStatus();
                });
        start.countDown();
        JsonNode page = mapper.readTree(listed.get(20, TimeUnit.SECONDS));
        assertThat(updated.get(20, TimeUnit.SECONDS)).isIn(200, 409);
        pool.shutdownNow();
        long openFromItems = 0;
        long openAmountFromItems = 0;
        for (JsonNode item : page.get("items")) {
            if ("OPEN".equals(item.get("status").asText())) {
                openFromItems++;
                openAmountFromItems += Long.parseLong(item.get("outstandingAmountMinor").asText());
            }
        }
        if (page.get("totalItems").asInt() <= page.get("size").asInt()) {
            assertThat(page.get("summary").get("openCount").asLong()).isEqualTo(openFromItems);
            assertThat(Long.parseLong(page.get("summary").get("openAmountMinor").asText()))
                    .isEqualTo(openAmountFromItems);
        }
        assertThat(page.get("items").size()).isLessThanOrEqualTo(page.get("size").asInt());
    }

    @Test
    void versionConflictDoesNotOverwrite() throws Exception {
        String created = createRegistered("/api/v1/payables", LocalDemoSeed.CP_PADARIA_FORNECEDOR, LocalDemoSeed.CAT_ALUGUEL, "Conflito");
        JsonNode json = mapper.readTree(created);
        mockMvc.perform(
                        patch("/api/v1/payables/" + json.get("id").asText())
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("""
                                        {
                                          "description":"Não deve gravar",
                                          "counterpartyId":"%s",
                                          "categoryId":"%s",
                                          "amountMinor":"1000",
                                          "currency":"BRL",
                                          "competenceDate":"2026-09-15",
                                          "dueDate":"2026-09-21",
                                          "version":0,
                                          "reason":"Versão velha de propósito"
                                        }
                                        """
                                        .formatted(LocalDemoSeed.CP_PADARIA_FORNECEDOR, LocalDemoSeed.CAT_ALUGUEL)))
                .andExpect(status().isConflict());
    }

    private String performCreate(CountDownLatch start, String key, String body, AtomicInteger oks) throws Exception {
        start.await(5, TimeUnit.SECONDS);
        MvcResult result = mockMvc.perform(
                        post("/api/v1/receivables")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("register", "true")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", key)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(body))
                .andReturn();
        if (result.getResponse().getStatus() == 200) {
            oks.incrementAndGet();
        }
        return result.getResponse().getContentAsString();
    }

    private String createDraft(String description) throws Exception {
        return mockMvc.perform(
                        post("/api/v1/receivables")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"description\":\"%s\"}".formatted(description)))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
    }

    private static String updateBody(String description, long version) {
        return """
                {
                  "description":"%s",
                  "counterpartyId":"%s",
                  "categoryId":"%s",
                  "amountMinor":"1000",
                  "currency":"BRL",
                  "competenceDate":"2026-09-15",
                  "dueDate":"2026-09-22",
                  "version":%s,
                  "reason":null
                }
                """
                .formatted(description, LocalDemoSeed.CP_PADARIA_CLIENTE, LocalDemoSeed.CAT_VENDA, version);
    }

    private String createRegistered(String path, UUID counterparty, UUID category, String description) throws Exception {
        return mockMvc.perform(
                        post(path)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("register", "true")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("""
                                        {
                                          "description":"%s",
                                          "counterpartyId":"%s",
                                          "categoryId":"%s",
                                          "amountMinor":"1000",
                                          "currency":"BRL",
                                          "competenceDate":"2026-09-15",
                                          "dueDate":"2026-09-22"
                                        }
                                        """
                                        .formatted(description, counterparty, category)))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
    }
}
