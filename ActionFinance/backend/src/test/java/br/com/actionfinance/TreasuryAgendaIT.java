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
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MvcResult;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import org.springframework.http.MediaType;

import java.math.BigDecimal;
import java.sql.Date;
import java.sql.Timestamp;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("local-demo")
@Testcontainers
class TreasuryAgendaIT {

    private static final String OPERATOR = "operator-demo-token-aaaaaaaaaaaaaaaaaaaa";
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
        registry.add("actionfinance.demo-auth.viewer-a-token", () -> "viewer-a-demo-token-bbbbbbbbbbbbbbbbbbbb");
        registry.add("actionfinance.demo-auth.viewer-b-token", () -> VIEWER_B);
        registry.add("actionfinance.demo-auth.operator-multi-token", () -> "operator-multi-token-dddddddddddddddddd");
        registry.add("actionfinance.clock.zone", () -> "America/Sao_Paulo");
    }

    @Autowired
    MockMvc mockMvc;

    @Autowired
    ObjectMapper mapper;

    @Autowired
    JdbcTemplate jdbc;

    @Test
    void readsTheCycleWithoutWriting() throws Exception {
        int titles = count("financial_title");
        int settlements = count("settlement");
        int movements = count("cash_movement");
        JsonNode summary = readJson("/api/v1/treasury/summary", OPERATOR, DemoPrincipalCatalog.COMPANY_A.toString());
        assertThat(summary.get("zone").asText()).isEqualTo("America/Sao_Paulo");
        assertThat(summary.get("note").asText()).contains("não se somam");
        assertThat(summary.get("obligations").get("receivableOpenMinor").asText()).isNotEqualTo(summary.get("realized").get("receivedMinor").asText());
        assertThat(summary.get("obligations").get("draftCount").asInt()).isGreaterThan(0);
        assertThat(summary.get("position").get("label").asText()).isEqualTo("Posição das contas ativas apuradas");
        assertThat(summary.get("position").get("known").asBoolean()).isTrue();
        assertThat(summary.get("position").has("knownMinor")).isTrue();
        assertThat(summary.get("position").get("limit").asText()).contains("Não é o saldo total");
        assertThat(summary.get("conference").get("meaning").asText()).contains("livro");

        JsonNode agenda = readJson("/api/v1/treasury/agenda?bucket=OVERDUE&size=5", OPERATOR, DemoPrincipalCatalog.COMPANY_A.toString());
        assertThat(agenda.get("buckets")).hasSize(5);
        long bucketSum = 0;
        for (JsonNode bucket : agenda.get("buckets")) {
            bucketSum += bucket.get("count").asLong();
        }
        assertThat(agenda.get("items").get("total").asLong()).isLessThanOrEqualTo(bucketSum);
        for (JsonNode item : agenda.get("items").get("items")) {
            assertThat(item.get("account").asText()).isEqualTo("Conta ainda não definida");
            assertThat(item.get("dueDate").asText()).isNotBlank();
        }
        JsonNode undated = readJson("/api/v1/treasury/agenda?bucket=UNDATED", OPERATOR, DemoPrincipalCatalog.COMPANY_A.toString());
        for (JsonNode item : undated.get("items").get("items")) {
            assertThat(item.get("dueDate").isNull()).isTrue();
        }
        mockMvc.perform(get("/api/v1/treasury/agenda")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_B.toString())
                        .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isForbidden());
        assertThat(count("financial_title")).isEqualTo(titles);
        assertThat(count("settlement")).isEqualTo(settlements);
        assertThat(count("cash_movement")).isEqualTo(movements);
    }

    @Test
    void positionIgnoresTheFutureAndEachIndicatorKeepsItsSet() throws Exception {
        LocalDate today = LocalDate.now(ZoneId.of("America/Sao_Paulo"));
        JsonNode before = readJson("/api/v1/treasury/summary", OPERATOR, DemoPrincipalCatalog.COMPANY_A.toString());
        String knownBefore = before.get("position").get("knownMinor").asText();
        long partialBefore = before.get("conference").get("partialCount").asLong();
        long divergentBefore = before.get("conference").get("divergentCount").asLong();
        long reviewBefore = before.get("conference").get("reviewCount").asLong();

        mockMvc.perform(post("/api/v1/financial-accounts")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .header("Authorization", "Bearer " + OPERATOR)
                        .header("Idempotency-Key", "future-opening-051")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"name":"Conta futura","type":"CASH","openedOn":"%s","openingBalanceMinor":"100"}
                                """.formatted(today.plusDays(1))))
                .andExpect(status().isBadRequest());

        futureMovement(LocalDemoSeed.ACCOUNT_A_BANK, 999999, today.plusDays(2));
        bareAccount("Conta sem saldo inicial", true, null, null);
        bareAccount("Conta inativa com valor", false, new BigDecimal("4242"), today.minusDays(3));
        bareAccount("Conta com saldo inicial futuro", true, new BigDecimal("7777"), today.plusDays(4));
        assertThatThrownByCurrency();

        JsonNode after = readJson("/api/v1/treasury/summary", OPERATOR, DemoPrincipalCatalog.COMPANY_A.toString());
        assertThat(after.get("position").get("knownMinor").asText()).isEqualTo(knownBefore);
        assertThat(after.get("position").get("known").asBoolean()).isTrue();
        assertThat(group(after, "SEM_SALDO_INICIAL")).anyMatch(name -> name.contains("sem saldo inicial"));
        assertThat(group(after, "INATIVA").toString()).contains("4242");
        assertThat(group(after, "SALDO_INICIAL_POSTERIOR")).anyMatch(name -> name.contains("futuro"));
        assertThat(after.get("position").get("limit").asText()).contains("contas ativas");

        JsonNode empty = readJson("/api/v1/treasury/summary", "operator-multi-token-dddddddddddddddddd", DemoPrincipalCatalog.COMPANY_C.toString());
        assertThat(empty.get("position").get("known").asBoolean()).isFalse();
        assertThat(empty.get("position").has("knownMinor")).isFalse();
        assertThat(empty.get("position").get("guidance").asText()).contains("Consulte as contas");

        JsonNode invalid = readJson("/api/v1/treasury/agenda?bucket=AMANHA&direction=TUDO", OPERATOR, DemoPrincipalCatalog.COMPANY_A.toString());
        assertThat(invalid.get("bucket").asText()).isEqualTo("OVERDUE");
        assertThat(invalid.get("direction").asText()).isEqualTo("ALL");
        assertThat(invalid.get("notice").asText()).contains("faixa").contains("direção");

        UUID movement = jdbc.queryForObject(
                "select id from actionfinance.cash_movement where account_id = ? and kind = 'OPENING'",
                UUID.class, LocalDemoSeed.ACCOUNT_A_BANK);
        UUID confirmed = batch("CONFIRMED", "relatorio-confirmado.csv");
        UUID withdrawn = batch("WITHDRAWN", "relatorio-retirado.csv");
        line(confirmed, movement, 10000, 5000, "parcial-051");
        line(confirmed, movement, 8500, 9000, "divergente-051");
        occurrence(confirmed, "IN_REVIEW", null);
        occurrence(withdrawn, "IN_REVIEW", null);
        JsonNode conference = readJson("/api/v1/treasury/summary", OPERATOR, DemoPrincipalCatalog.COMPANY_A.toString());
        assertThat(conference.get("conference").get("partialCount").asLong()).isEqualTo(partialBefore + 1);
        assertThat(conference.get("conference").get("divergentCount").asLong()).isEqualTo(divergentBefore + 1);
        assertThat(conference.get("conference").get("reviewCount").asLong()).isEqualTo(reviewBefore + 1);
        assertThat(conference.get("conference").get("reviewUnit").asText()).isEqualTo("OCCURRENCE");
        assertThat(conference.get("conference").get("reviewBatches").toString()).contains("relatorio-confirmado.csv");
        assertThat(conference.get("conference").get("reviewBatches").toString()).doesNotContain("relatorio-retirado.csv");
    }

    private java.util.List<String> group(JsonNode summary, String reason) {
        java.util.List<String> names = new java.util.ArrayList<>();
        for (JsonNode exclusion : summary.get("position").get("exclusions")) {
            if (reason.equals(exclusion.get("reason").asText())) {
                for (JsonNode account : exclusion.get("accounts")) {
                    names.add(account.toString());
                }
            }
        }
        return names;
    }

    private void futureMovement(UUID accountId, long signed, LocalDate date) {
        UUID settlementId = UUID.randomUUID();
        Instant now = Instant.parse("2026-10-16T15:00:00Z");
        jdbc.update(
                """
                insert into actionfinance.settlement (
                    id, tenant_id, company_id, account_id, direction, amount_minor, currency,
                    effective_date, method, note, origin_kind, recorded_at, recorded_by, actor_display_name)
                values (?,?,?,?,'RECEIVABLE',?,'BRL',?,'PIX','Futuro','MANUAL',?,?,?)
                """,
                settlementId, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, accountId,
                BigDecimal.valueOf(Math.abs(signed)), Date.valueOf(date),
                Timestamp.from(now), DemoPrincipalCatalog.OPERATOR_A, "Ensaio");
        jdbc.update(
                """
                insert into actionfinance.cash_movement (
                    id, tenant_id, company_id, account_id, kind, signed_amount_minor, currency,
                    effective_date, recorded_at, recorded_by, settlement_id, reversal_id, description)
                values (?,?,?,?,'SETTLEMENT',?,'BRL',?,?,?, ?, null, 'Movimento futuro')
                """,
                UUID.randomUUID(), DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, accountId,
                signed, Date.valueOf(date), Timestamp.from(now), DemoPrincipalCatalog.OPERATOR_A, settlementId);
    }

    private void bareAccount(String name, boolean active, BigDecimal opening, LocalDate openingOn) {
        UUID id = UUID.randomUUID();
        Instant now = Instant.parse("2026-10-16T15:00:00Z");
        jdbc.update(
                """
                insert into actionfinance.financial_account (
                    id, tenant_id, company_id, code, name, type, currency, active, opened_on,
                    version, created_at, updated_at, created_by, updated_by)
                values (?,?,?,?,?,'OTHER','BRL',?,?,1,?,?,?,?)
                """,
                id, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, "CTA-" + id, name, active,
                Date.valueOf(openingOn == null ? LocalDate.of(2026, 10, 1) : openingOn),
                Timestamp.from(now), Timestamp.from(now), DemoPrincipalCatalog.OPERATOR_A, DemoPrincipalCatalog.OPERATOR_A);
        if (opening != null && openingOn != null) {
            jdbc.update(
                    """
                    insert into actionfinance.cash_movement (
                        id, tenant_id, company_id, account_id, kind, signed_amount_minor, currency,
                        effective_date, recorded_at, recorded_by, settlement_id, reversal_id, description)
                    values (?,?,?,?,'OPENING',?,'BRL',?,?,?, null, null, 'Saldo inicial informado')
                    """,
                    UUID.randomUUID(), DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, id,
                    opening, Date.valueOf(openingOn), Timestamp.from(now), DemoPrincipalCatalog.OPERATOR_A);
        }
    }

    private void assertThatThrownByCurrency() {
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> jdbc.update(
                """
                insert into actionfinance.financial_account (
                    id, tenant_id, company_id, code, name, type, currency, active, opened_on,
                    version, created_at, updated_at, created_by, updated_by)
                values (?,?,?,?,?,'OTHER','USD',true,'2026-10-01',1,now(),now(),?,?)
                """,
                UUID.randomUUID(), DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A,
                "CTA-USD", "Conta em dólar", DemoPrincipalCatalog.OPERATOR_A, DemoPrincipalCatalog.OPERATOR_A))
                .hasMessageContaining("currency");
    }

    private UUID batch(String status, String fileName) {
        UUID id = UUID.randomUUID();
        String hex = "a".repeat(64);
        jdbc.update(
                """
                insert into actionfinance.statement_batch (
                    id, tenant_id, company_id, account_id, profile_id, parser_version, file_sha256, file_name,
                    status, preview_token, preview_json, created_count, enriched_count, unchanged_count, rejected_count,
                    created_at, created_by)
                values (?,?,?,?,'mp-account-money-csv-1','1',?,?, ?,?,'{}',0,0,0,0,now(),?)
                """,
                id, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, LocalDemoSeed.ACCOUNT_A_BANK,
                hex, fileName, status, "b".repeat(64), DemoPrincipalCatalog.OPERATOR_A);
        return id;
    }

    private void line(UUID batchId, UUID movementId, long net, long allocated, String key) {
        UUID lineId = UUID.randomUUID();
        jdbc.update(
                """
                insert into actionfinance.statement_line (
                    id, tenant_id, company_id, account_id, batch_id, event_key, content_hash, source_id, record_type,
                    description, effective_on, direction, event_kind, balance_effect, gross_minor, gross_absent,
                    fee_minor, fee_absent, net_minor, net_absent, currency, currency_assumed, classification_state,
                    initiative_state, import_status, source_line_number, created_at, updated_at, availability)
                values (?,?,?,?,?,?,?,'src','SETTLEMENT','Linha','2026-10-02','IN','SETTLEMENT','AFFECTS',
                        ?,false,0,false,?,false,'BRL',false,'UNCLASSIFIED','UNASSIGNED','ACTIVE',1,now(),now(),'RELEASED')
                """,
                lineId, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, LocalDemoSeed.ACCOUNT_A_BANK, batchId,
                key, (key.startsWith("parcial") ? "c" : "e").repeat(64), net, net);
        jdbc.update(
                """
                insert into actionfinance.statement_book_allocation (
                    id, tenant_id, company_id, line_id, group_id, movement_id, allocated_minor, movement_sign,
                    status, version, updated_at, updated_by)
                values (?,?,?,?,null,?,?,1,'ACTIVE',1,now(),?)
                """,
                UUID.randomUUID(), DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, lineId, movementId,
                BigDecimal.valueOf(allocated), DemoPrincipalCatalog.OPERATOR_A);
    }

    private void occurrence(UUID batchId, String consolidation, UUID lineId) {
        jdbc.update(
                """
                insert into actionfinance.statement_occurrence (
                    id, tenant_id, company_id, batch_id, source_line_number, document_key, content_hash, availability,
                    consolidation, in_partial_total, line_id, source_id, record_type, direction, event_kind,
                    gross_absent, fee_absent, net_absent, raw_text, truncated, created_at)
                values (?,?,?,?,1,?,?,'RELEASED',?,false,?,?, 'SETTLEMENT','IN','SETTLEMENT',true,true,true,'linha',false,now())
                """,
                UUID.randomUUID(), DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, batchId,
                "doc-" + batchId, "d".repeat(64), consolidation, lineId, "src-" + batchId);
    }

    private JsonNode readJson(String path, String token, String companyId) throws Exception {
        MvcResult result = mockMvc.perform(get(path)
                        .param("companyId", companyId)
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andReturn();
        return mapper.readTree(result.getResponse().getContentAsString());
    }

    private int count(String table) {
        return jdbc.queryForObject("select count(*) from actionfinance." + table, Integer.class);
    }
}
