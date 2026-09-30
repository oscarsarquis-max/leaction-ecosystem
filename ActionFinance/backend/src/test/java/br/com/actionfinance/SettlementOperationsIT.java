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
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.math.BigDecimal;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("local-demo")
@Testcontainers
class SettlementOperationsIT {

    private static final String OPERATOR = "operator-demo-token-aaaaaaaaaaaaaaaaaaaa";
    private static final String VIEWER_A = "viewer-a-demo-token-bbbbbbbbbbbbbbbbbbbb";

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
        registry.add("actionfinance.demo-auth.viewer-b-token", () -> "viewer-b-demo-token-cccccccccccccccccccc");
        registry.add("actionfinance.clock.zone", () -> "America/Sao_Paulo");
        registry.add("actionfinance.clock.fixed-instant", () -> "2026-09-15T15:00:00Z");
    }

    @Autowired
    MockMvc mockMvc;

    @Autowired
    ObjectMapper mapper;

    @Autowired
    JdbcTemplate jdbc;

    @Test
    void receivableJourneyPartialThenFullThenReverse() throws Exception {
        journey("/api/v1/receivables", LocalDemoSeed.CP_PADARIA_CLIENTE, LocalDemoSeed.CAT_VENDA, "Jornada a receber");
    }

    @Test
    void payableJourneyPartialThenFullThenReverse() throws Exception {
        journey("/api/v1/payables", LocalDemoSeed.CP_PADARIA_FORNECEDOR, LocalDemoSeed.CAT_INSUMOS, "Jornada a pagar");
    }

    @Test
    void seedExamplesAreIdentifiable() throws Exception {
        mockMvc.perform(
                        get("/api/v1/receivables/" + LocalDemoSeed.TITLE_REC_PARTIAL)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.amountMinor").value("15000"))
                .andExpect(jsonPath("$.settledAmountMinor").value("5000"))
                .andExpect(jsonPath("$.outstandingAmountMinor").value("10000"))
                .andExpect(jsonPath("$.settlementStatus").value("PARTIAL"));
        mockMvc.perform(
                        get("/api/v1/payables/" + LocalDemoSeed.TITLE_PAG_SETTLED)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.settlementStatus").value("SETTLED"))
                .andExpect(jsonPath("$.overdue").value(false));
        mockMvc.perform(
                        get("/api/v1/financial-accounts")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[?(@.id=='" + LocalDemoSeed.ACCOUNT_A_BANK + "')]").exists());
        mockMvc.perform(
                        get("/api/v1/financial-accounts/" + LocalDemoSeed.ACCOUNT_A_BANK + "/movements")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("from", "2026-08-01")
                                .param("to", "2026-09-15")
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.previousBalanceMinor").exists())
                .andExpect(jsonPath("$.periodEndBalanceMinor").exists())
                .andExpect(jsonPath("$.currentBalanceMinor").exists());
        mockMvc.perform(
                        get("/api/v1/financial-accounts")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + VIEWER_A))
                .andExpect(status().isOk());
        mockMvc.perform(
                        post("/api/v1/financial-accounts")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + VIEWER_A)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"name\":\"Não deve\",\"type\":\"BANK\",\"openedOn\":\"2026-09-01\",\"openingBalanceMinor\":\"0\"}"))
                .andExpect(status().isForbidden());
    }

    @Test
    void rejectsInvalidSettlementsAndAllowsReversalOnInactiveAccount() throws Exception {
        String created = createTitle("/api/v1/receivables", "15000", "Bloqueios");
        JsonNode title = mapper.readTree(created);
        mockMvc.perform(
                        post("/api/v1/receivables/" + title.get("id").asText() + "/settlements")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(settlementBody(LocalDemoSeed.ACCOUNT_A_BANK, "0", "2026-09-15", title.get("version").asLong())))
                .andExpect(status().isBadRequest());
        mockMvc.perform(
                        post("/api/v1/receivables/" + title.get("id").asText() + "/settlements")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(settlementBody(LocalDemoSeed.ACCOUNT_A_BANK, "20000", "2026-09-15", title.get("version").asLong())))
                .andExpect(status().isBadRequest());
        mockMvc.perform(
                        post("/api/v1/receivables/" + title.get("id").asText() + "/settlements")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(settlementBody(LocalDemoSeed.ACCOUNT_A_BANK, "1000", "2026-09-16", title.get("version").asLong())))
                .andExpect(status().isBadRequest());
        mockMvc.perform(
                        post("/api/v1/receivables/" + LocalDemoSeed.TITLE_REC_DRAFT + "/settlements")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(settlementBody(LocalDemoSeed.ACCOUNT_A_BANK, "1000", "2026-09-15", 1)))
                .andExpect(status().isBadRequest());

        String cash = mockMvc.perform(
                        post("/api/v1/financial-accounts")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"name\":\"Caixa para inativar\",\"type\":\"CASH\",\"openedOn\":\"2026-09-01\",\"openingBalanceMinor\":\"-500\"}"))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        JsonNode account = mapper.readTree(cash);
        String first = mockMvc.perform(
                        post("/api/v1/receivables/" + title.get("id").asText() + "/settlements")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(settlementBody(account.get("id").asText(), "4000", "2026-09-15", title.get("version").asLong())))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        JsonNode settlement = mapper.readTree(first);
        mockMvc.perform(
                        patch("/api/v1/financial-accounts/" + account.get("id").asText())
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"version\":%d,\"active\":false}".formatted(account.get("version").asLong())))
                .andExpect(status().isOk());
        mockMvc.perform(
                        post("/api/v1/receivables/" + title.get("id").asText() + "/settlements")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(settlementBody(account.get("id").asText(), "1000", "2026-09-15", settlement.get("titleVersion").asLong())))
                .andExpect(status().isBadRequest());
        mockMvc.perform(
                        post("/api/v1/settlements/" + settlement.get("id").asText() + "/reversal")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"effectiveDate\":\"2026-09-15\",\"reason\":\"Corrigir baixa em conta inativa\",\"version\":%d}"
                                        .formatted(settlement.get("titleVersion").asLong())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.reversed").value(true));
    }

    @Test
    void settlementLocksPrincipalAndBlocksCancelUntilReversed() throws Exception {
        String created = createTitle("/api/v1/receivables", "15000", "Trava de principal");
        JsonNode title = mapper.readTree(created);
        mockMvc.perform(
                        post("/api/v1/receivables/" + title.get("id").asText() + "/settlements")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(settlementBody(LocalDemoSeed.ACCOUNT_A_BANK, "5000", "2026-09-15", title.get("version").asLong())))
                .andExpect(status().isOk());
        mockMvc.perform(
                        patch("/api/v1/receivables/" + title.get("id").asText())
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("""
                                        {
                                          "description":"Não pode mudar valor",
                                          "counterpartyId":"%s",
                                          "categoryId":"%s",
                                          "amountMinor":"16000",
                                          "currency":"BRL",
                                          "competenceDate":"2026-09-15",
                                          "dueDate":"2026-09-22",
                                          "version":2,
                                          "reason":"Tentativa indevida"
                                        }
                                        """
                                        .formatted(LocalDemoSeed.CP_PADARIA_CLIENTE, LocalDemoSeed.CAT_VENDA)))
                .andExpect(status().isBadRequest());
        mockMvc.perform(
                        post("/api/v1/receivables/" + title.get("id").asText() + "/cancel")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"version\":2,\"reason\":\"Ainda tem baixa\"}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void concurrentSettlementsNeverExceedPrincipalAndReplayIsStable() throws Exception {
        String created = createTitle("/api/v1/receivables", "15000", "Concorrência de baixa");
        JsonNode title = mapper.readTree(created);
        String body = settlementBody(LocalDemoSeed.ACCOUNT_A_BANK, "10000", "2026-09-15", title.get("version").asLong());
        CountDownLatch start = new CountDownLatch(1);
        var pool = Executors.newFixedThreadPool(2);
        Future<Integer> left = pool.submit(() -> postSettlement(start, title.get("id").asText(), body, UUID.randomUUID().toString()));
        Future<Integer> right = pool.submit(() -> postSettlement(start, title.get("id").asText(), body, UUID.randomUUID().toString()));
        start.countDown();
        int a = left.get(20, TimeUnit.SECONDS);
        int b = right.get(20, TimeUnit.SECONDS);
        pool.shutdownNow();
        assertThat(java.util.List.of(a, b)).contains(200);
        assertThat(java.util.Set.of(a, b)).contains(409);
        JsonNode after = mapper.readTree(
                mockMvc.perform(
                                get("/api/v1/receivables/" + title.get("id").asText())
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .header("Authorization", "Bearer " + OPERATOR))
                        .andReturn()
                        .getResponse()
                        .getContentAsString());
        assertThat(after.get("settledAmountMinor").asText()).isEqualTo("10000");
        assertThat(after.get("outstandingAmountMinor").asText()).isEqualTo("5000");
        Integer settlementRows = jdbc.queryForObject(
                "select count(*) from actionfinance.settlement_allocation where title_id = ?::uuid",
                Integer.class,
                UUID.fromString(title.get("id").asText()));
        Integer movementRows = jdbc.queryForObject(
                """
                select count(*) from actionfinance.cash_movement m
                join actionfinance.settlement_allocation a on a.settlement_id = m.settlement_id
                where a.title_id = ?::uuid and m.kind = 'SETTLEMENT'
                """,
                Integer.class,
                UUID.fromString(title.get("id").asText()));
        Integer historyRows = jdbc.queryForObject(
                "select count(*) from actionfinance.financial_title_history where title_id = ?::uuid and action = 'SETTLEMENT_RECORDED'",
                Integer.class,
                UUID.fromString(title.get("id").asText()));
        assertThat(settlementRows).isEqualTo(1);
        assertThat(movementRows).isEqualTo(1);
        assertThat(historyRows).isEqualTo(1);

        String key = "replay-" + UUID.randomUUID();
        String rest = settlementBody(LocalDemoSeed.ACCOUNT_A_BANK, "5000", "2026-09-15", after.get("version").asLong());
        MvcResult first = mockMvc.perform(
                        post("/api/v1/receivables/" + title.get("id").asText() + "/settlements")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", key)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(rest))
                .andExpect(status().isOk())
                .andReturn();
        String id = mapper.readTree(first.getResponse().getContentAsString()).get("id").asText();
        mockMvc.perform(
                        post("/api/v1/receivables/" + title.get("id").asText() + "/settlements")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", key)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(rest))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(id));
        Integer movements = jdbc.queryForObject(
                "select count(*) from actionfinance.cash_movement where kind='SETTLEMENT' and settlement_id = ?::uuid",
                Integer.class,
                UUID.fromString(id));
        assertThat(movements).isEqualTo(1);
    }

    @Test
    void replayCreateAccountKeepsSingleOpeningMovement() throws Exception {
        String key = "account-create-" + UUID.randomUUID();
        String body =
                "{\"name\":\"Conta COR 001 Replay\",\"type\":\"CASH\",\"openedOn\":\"2026-09-01\",\"openingBalanceMinor\":\"25000\"}";
        String first = mockMvc.perform(
                        post("/api/v1/financial-accounts")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", key)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(body))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        String id = mapper.readTree(first).get("id").asText();
        mockMvc.perform(
                        post("/api/v1/financial-accounts")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", key)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(id));
        Integer accounts = jdbc.queryForObject(
                "select count(*) from actionfinance.financial_account where name = ?",
                Integer.class,
                "Conta COR 001 Replay");
        Integer openings = jdbc.queryForObject(
                "select count(*) from actionfinance.cash_movement where account_id = ?::uuid and kind = 'OPENING'",
                Integer.class,
                UUID.fromString(id));
        assertThat(accounts).isEqualTo(1);
        assertThat(openings).isEqualTo(1);
    }

    @Test
    void replayUpdateAccountIsStable() throws Exception {
        String created = mockMvc.perform(
                        post("/api/v1/financial-accounts")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"name\":\"Conta para renomear\",\"type\":\"BANK\",\"openedOn\":\"2026-09-01\",\"openingBalanceMinor\":\"1000\"}"))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        JsonNode account = mapper.readTree(created);
        String key = "account-update-" + UUID.randomUUID();
        String body = "{\"name\":\"Conta renomeada COR\",\"version\":%d}".formatted(account.get("version").asLong());
        String first = mockMvc.perform(
                        patch("/api/v1/financial-accounts/" + account.get("id").asText())
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", key)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(body))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        mockMvc.perform(
                        patch("/api/v1/financial-accounts/" + account.get("id").asText())
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", key)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.version").value(mapper.readTree(first).get("version").asLong()))
                .andExpect(jsonPath("$.name").value("Conta renomeada COR"));
        Integer history = jdbc.queryForObject(
                "select count(*) from actionfinance.financial_account_history where account_id = ?::uuid and action = 'RENAMED'",
                Integer.class,
                UUID.fromString(account.get("id").asText()));
        assertThat(history).isEqualTo(1);
    }

    @Test
    void concurrentReversalsProduceSingleInverseMovement() throws Exception {
        String created = createTitle("/api/v1/receivables", "15000", "Estorno concorrente");
        JsonNode title = mapper.readTree(created);
        JsonNode settlement = mapper.readTree(record("/api/v1/receivables", title.get("id").asText(), "5000", title.get("version").asLong()));
        String body = "{\"effectiveDate\":\"2026-09-15\",\"reason\":\"Estorno concorrente de prova\",\"version\":%d}"
                .formatted(settlement.get("titleVersion").asLong());
        CountDownLatch start = new CountDownLatch(1);
        var pool = Executors.newFixedThreadPool(2);
        Future<Integer> left = pool.submit(() -> postReversal(start, settlement.get("id").asText(), body, UUID.randomUUID().toString()));
        Future<Integer> right = pool.submit(() -> postReversal(start, settlement.get("id").asText(), body, UUID.randomUUID().toString()));
        start.countDown();
        int a = left.get(20, TimeUnit.SECONDS);
        int b = right.get(20, TimeUnit.SECONDS);
        pool.shutdownNow();
        assertThat(java.util.List.of(a, b)).contains(200);
        assertThat(java.util.Set.of(a, b)).contains(409);
        Integer reversals = jdbc.queryForObject(
                "select count(*) from actionfinance.settlement_reversal where settlement_id = ?::uuid",
                Integer.class,
                UUID.fromString(settlement.get("id").asText()));
        Integer inverse = jdbc.queryForObject(
                "select count(*) from actionfinance.cash_movement where settlement_id = ?::uuid and kind = 'REVERSAL'",
                Integer.class,
                UUID.fromString(settlement.get("id").asText()));
        assertThat(reversals).isEqualTo(1);
        assertThat(inverse).isEqualTo(1);
    }

    @Test
    void movementsStayConsistentAcrossPagesRetroactiveAndConcurrentWrite() throws Exception {
        String cash = mockMvc.perform(
                        post("/api/v1/financial-accounts")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"name\":\"Conta extrato COR\",\"type\":\"BANK\",\"openedOn\":\"2026-09-01\",\"openingBalanceMinor\":\"100000\"}"))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        JsonNode account = mapper.readTree(cash);
        String created = createTitle("/api/v1/receivables", "25000", "Extrato paginado COR");
        JsonNode title = mapper.readTree(created);
        long version = title.get("version").asLong();
        for (int i = 0; i < 20; i++) {
            JsonNode settlement = mapper.readTree(
                    mockMvc.perform(
                                    post("/api/v1/receivables/" + title.get("id").asText() + "/settlements")
                                            .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                            .header("Authorization", "Bearer " + OPERATOR)
                                            .header("Idempotency-Key", UUID.randomUUID().toString())
                                            .contentType(MediaType.APPLICATION_JSON)
                                            .content(settlementBody(account.get("id").asText(), "1000", "2026-09-15", version)))
                            .andExpect(status().isOk())
                            .andReturn()
                            .getResponse()
                            .getContentAsString());
            version = settlement.get("titleVersion").asLong();
        }
        JsonNode retroactive = mapper.readTree(
                mockMvc.perform(
                                post("/api/v1/receivables/" + title.get("id").asText() + "/settlements")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .header("Authorization", "Bearer " + OPERATOR)
                                        .header("Idempotency-Key", UUID.randomUUID().toString())
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content(settlementBody(account.get("id").asText(), "2000", "2026-09-05", version)))
                        .andExpect(status().isOk())
                        .andReturn()
                        .getResponse()
                        .getContentAsString());
        CountDownLatch start = new CountDownLatch(1);
        var pool = Executors.newFixedThreadPool(2);
        Future<JsonNode> snapshot = pool.submit(() -> {
            start.await(5, TimeUnit.SECONDS);
            return mapper.readTree(
                    mockMvc.perform(
                                    get("/api/v1/financial-accounts/" + account.get("id").asText() + "/movements")
                                            .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                            .param("from", "2026-09-01")
                                            .param("to", "2026-09-15")
                                            .param("page", "0")
                                            .param("size", "50")
                                            .header("Authorization", "Bearer " + OPERATOR))
                            .andExpect(status().isOk())
                            .andReturn()
                            .getResponse()
                            .getContentAsString());
        });
        Future<Integer> racingWrite = pool.submit(() -> {
            start.await(5, TimeUnit.SECONDS);
            return mockMvc.perform(
                            post("/api/v1/receivables/" + title.get("id").asText() + "/settlements")
                                    .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                    .header("Authorization", "Bearer " + OPERATOR)
                                    .header("Idempotency-Key", UUID.randomUUID().toString())
                                    .contentType(MediaType.APPLICATION_JSON)
                                    .content(settlementBody(
                                            account.get("id").asText(),
                                            "1000",
                                            "2026-09-15",
                                            retroactive.get("titleVersion").asLong())))
                    .andReturn()
                    .getResponse()
                    .getStatus();
        });
        start.countDown();
        JsonNode page = snapshot.get(20, TimeUnit.SECONDS);
        racingWrite.get(20, TimeUnit.SECONDS);
        pool.shutdownNow();
        assertMovementIdentity(page);
        JsonNode pageZero = mapper.readTree(
                mockMvc.perform(
                                get("/api/v1/financial-accounts/" + account.get("id").asText() + "/movements")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .param("from", "2026-09-01")
                                        .param("to", "2026-09-15")
                                        .param("page", "0")
                                        .param("size", "20")
                                        .header("Authorization", "Bearer " + OPERATOR))
                        .andExpect(status().isOk())
                        .andReturn()
                        .getResponse()
                        .getContentAsString());
        JsonNode pageOne = mapper.readTree(
                mockMvc.perform(
                                get("/api/v1/financial-accounts/" + account.get("id").asText() + "/movements")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .param("from", "2026-09-01")
                                        .param("to", "2026-09-15")
                                        .param("page", "1")
                                        .param("size", "20")
                                        .header("Authorization", "Bearer " + OPERATOR))
                        .andExpect(status().isOk())
                        .andReturn()
                        .getResponse()
                        .getContentAsString());
        assertThat(pageZero.get("previousBalanceMinor").asText()).isEqualTo(pageOne.get("previousBalanceMinor").asText());
        assertThat(pageZero.get("periodEndBalanceMinor").asText()).isEqualTo(pageOne.get("periodEndBalanceMinor").asText());
        assertThat(pageZero.get("currentBalanceMinor").asText()).isEqualTo(pageOne.get("currentBalanceMinor").asText());
        assertThat(pageZero.get("items").get(0).get("kind").asText()).isEqualTo("OPENING");
        boolean sawRetroactive = false;
        for (JsonNode item : page.get("items")) {
            if ("2026-09-05".equals(item.get("effectiveDate").asText()) && "SETTLEMENT".equals(item.get("kind").asText())) {
                sawRetroactive = true;
            }
        }
        assertThat(sawRetroactive).isTrue();
    }

    @Test
    void foreignKeysRejectCrossCompanyLinks() {
        assertThatThrownBy(
                        () -> jdbc.update(
                                """
                                insert into actionfinance.settlement_allocation (
                                    id, tenant_id, company_id, settlement_id, title_id, amount_minor)
                                values (?,?,?,?,?,100)
                                """,
                                UUID.randomUUID(),
                                DemoPrincipalCatalog.TENANT_A,
                                DemoPrincipalCatalog.COMPANY_A,
                                LocalDemoSeed.SETTLEMENT_PARTIAL,
                                LocalDemoSeed.TITLE_ATELIE_REC))
                .isInstanceOf(Exception.class);
    }

    private void journey(String path, UUID counterparty, UUID category, String description) throws Exception {
        String created = createTitle(path, "15000", description);
        JsonNode title = mapper.readTree(created);
        JsonNode first = mapper.readTree(record(path, title.get("id").asText(), "5000", title.get("version").asLong()));
        assertThat(first.get("titleOutstandingAmountMinor").asText()).isEqualTo("10000");
        JsonNode second = mapper.readTree(record(path, title.get("id").asText(), "10000", first.get("titleVersion").asLong()));
        assertThat(second.get("titleOutstandingAmountMinor").asText()).isEqualTo("0");
        mockMvc.perform(
                        get(path + "/" + title.get("id").asText())
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(jsonPath("$.settlementStatus").value("SETTLED"))
                .andExpect(jsonPath("$.overdue").value(false));
        mockMvc.perform(
                        post("/api/v1/settlements/" + first.get("id").asText() + "/reversal")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"effectiveDate\":\"2026-09-15\",\"reason\":\"Estorno da baixa de 50\",\"version\":%d}"
                                        .formatted(second.get("titleVersion").asLong())))
                .andExpect(status().isOk());
        mockMvc.perform(
                        get(path + "/" + title.get("id").asText())
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(jsonPath("$.settledAmountMinor").value("10000"))
                .andExpect(jsonPath("$.outstandingAmountMinor").value("5000"));
    }

    private String record(String path, String titleId, String amount, long version) throws Exception {
        return mockMvc.perform(
                        post(path + "/" + titleId + "/settlements")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(settlementBody(LocalDemoSeed.ACCOUNT_A_BANK, amount, "2026-09-15", version)))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
    }

    private int postReversal(CountDownLatch start, String settlementId, String body, String key) throws Exception {
        start.await(5, TimeUnit.SECONDS);
        return mockMvc.perform(
                        post("/api/v1/settlements/" + settlementId + "/reversal")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", key)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(body))
                .andReturn()
                .getResponse()
                .getStatus();
    }

    private static void assertMovementIdentity(JsonNode page) {
        BigDecimal previous = new BigDecimal(page.get("previousBalanceMinor").asText());
        BigDecimal periodEnd = new BigDecimal(page.get("periodEndBalanceMinor").asText());
        BigDecimal inflow = BigDecimal.ZERO;
        BigDecimal outflow = BigDecimal.ZERO;
        BigDecimal running = previous;
        for (JsonNode item : page.get("items")) {
            BigDecimal in = new BigDecimal(item.get("inflowMinor").asText());
            BigDecimal out = new BigDecimal(item.get("outflowMinor").asText());
            inflow = inflow.add(in);
            outflow = outflow.add(out);
            running = running.add(in).subtract(out);
            assertThat(new BigDecimal(item.get("balanceAfterMinor").asText())).isEqualByComparingTo(running);
        }
        assertThat(previous.add(inflow).subtract(outflow)).isEqualByComparingTo(periodEnd);
        assertThat(page.get("currentBalanceMinor").isTextual() || page.get("currentBalanceMinor").isNumber()).isTrue();
    }

    private int postSettlement(CountDownLatch start, String titleId, String body, String key) throws Exception {
        start.await(5, TimeUnit.SECONDS);
        return mockMvc.perform(
                        post("/api/v1/receivables/" + titleId + "/settlements")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .header("Idempotency-Key", key)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(body))
                .andReturn()
                .getResponse()
                .getStatus();
    }

    private String createTitle(String path, String amount, String description) throws Exception {
        UUID counterparty = path.contains("payables") ? LocalDemoSeed.CP_PADARIA_FORNECEDOR : LocalDemoSeed.CP_PADARIA_CLIENTE;
        UUID category = path.contains("payables") ? LocalDemoSeed.CAT_INSUMOS : LocalDemoSeed.CAT_VENDA;
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
                                          "amountMinor":"%s",
                                          "currency":"BRL",
                                          "competenceDate":"2026-09-15",
                                          "dueDate":"2026-09-22"
                                        }
                                        """
                                        .formatted(description, counterparty, category, amount)))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
    }

    private static String settlementBody(Object accountId, String amount, String date, long version) {
        return """
                {
                  "accountId":"%s",
                  "amountMinor":"%s",
                  "effectiveDate":"%s",
                  "method":"PIX",
                  "note":"Registro manual de teste",
                  "version":%d
                }
                """
                .formatted(accountId, amount, date, version);
    }
}
