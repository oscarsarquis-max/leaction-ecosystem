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
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("local-demo")
@Testcontainers
class StatementObservationIT {

    private static final String OPERATOR = "operator-demo-token-aaaaaaaaaaaaaaaaaaaa";
    private static final String VIEWER = "viewer-a-demo-token-bbbbbbbbbbbbbbbbbbbb";
    private static final String VIEWER_B = "viewer-b-demo-token-cccccccccccccccccccc";
    private static final String HEADER = """
            DATE,SOURCE_ID,RECORD_TYPE,EXTERNAL_REFERENCE,DESCRIPTION,NET_CREDIT_AMOUNT,NET_DEBIT_AMOUNT,GROSS_AMOUNT,MP_FEE_AMOUNT,CURRENCY,ACCOUNT_EXTERNAL_REF
            """;

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
        registry.add("actionfinance.demo-auth.viewer-a-token", () -> VIEWER);
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
    void importsObservationsWithoutCreatingFinanceMovements() throws Exception {
        int titles = count("financial_title");
        int settlements = count("settlement");
        int movements = count("cash_movement");
        UUID runId = UUID.randomUUID();
        jdbc.update(
                """
                insert into actionfinance.pay_receipt_sync_run (
                    id, tenant_id, company_id, origin_system, environment, status, root_correlation_id,
                    page_count, imported_count, updated_count, review_count, started_at, created_at, updated_at
                ) values (?, ?, ?, 'ACTIONHUB_PAY', 'HOMOLOG', 'SUCCESS', 'corr-sint-029', 0, 0, 0, 0, now(), now(), now())
                """,
                runId, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A);
        insertReceipt(runId, "order-sint-100", "order-sint-100", "pay-sint-100", 9000L, 8500L, "2026-10-01T12:00:00Z");
        insertReceipt(runId, "order-sint-fraco", "order-sint-fraco", null, 1200L, 1200L, "2026-10-03T12:00:00Z");
        insertReceipt(runId, "order-sint-falso-1", "order-sint-falso-1", null, 4000L, 4000L, "2026-10-04T12:00:00Z");
        insertReceipt(runId, "order-sint-falso-2", "order-sint-falso-2", null, 4000L, 4000L, "2026-10-04T13:00:00Z");
        insertReceipt(runId, "pay-sint-pedido", "outro-pedido", null, 100L, 100L, "2026-10-08T12:00:00Z");

        mockMvc.perform(post("/api/v1/statement-links")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .header("Authorization", "Bearer " + OPERATOR)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"accountId":"%s","externalRef":"mp-conta-sintetica","provenance":"vinculo sintetico de laboratorio"}
                                """.formatted(LocalDemoSeed.ACCOUNT_A_BANK)))
                .andExpect(status().isOk());

        JsonNode preview = preview(mainFile());
        assertThat(preview.get("recognized").asBoolean()).isTrue();
        assertThat(preview.get("issues").toString()).contains("Sem SOURCE_ID").contains("sem regra de conversão").contains("mesmo conteúdo");
        JsonNode confirmed = confirm(preview, "confirm-sint-029-a", "");
        assertThat(confirmed.get("created").asInt()).isEqualTo(7);
        assertThat(confirmed.get("accountAttestation").asText()).isEqualTo("FILE_REFERENCE");
        assertThat(confirmed.get("notImported").asInt()).isGreaterThan(0);
        JsonNode replay = confirm(preview, "confirm-sint-029-a", "");
        assertThat(replay.get("created").asInt()).isEqualTo(7);
        assertThat(countLines()).isEqualTo(7);

        JsonNode listed = lines("");
        assertThat(listed.get("creditMinor").asText()).isEqualTo("22300");
        assertThat(listed.get("debitMinor").asText()).isEqualTo("350");
        assertThat(listed.get("availabilityCount").asInt()).isZero();
        assertThat(listed.get("totalBasisText").asText()).contains("Não é variação do saldo total");
        assertThat(listed.get("amountAbsentCount").asInt()).isEqualTo(1);
        assertThat(listed.get("total").asInt()).isEqualTo(7);
        JsonNode settlement = find(listed, "pay-sint-100", "SETTLEMENT");
        assertThat(settlement.get("netMinor").asLong()).isEqualTo(8500L);
        assertThat(settlement.get("feeMinor").asLong()).isEqualTo(500L);
        assertThat(settlement.get("suggestions").toString()).contains("QUALIFIED").contains("MP_PAYMENT");
        assertThat(listed.get("items").toString()).doesNotContain("RELEASE");
        assertThat(find(listed, "pay-sint-fraco", "SETTLEMENT").get("suggestions").toString()).contains("WEAK");
        assertThat(find(listed, "pay-sint-falso", "SETTLEMENT").get("suggestions")).isEmpty();
        assertThat(find(listed, "pay-sint-pedido", "SETTLEMENT").get("suggestions")).isEmpty();
        assertThat(find(listed, "pay-sint-ausente", "SETTLEMENT").get("netAbsent").asBoolean()).isTrue();
        assertThat(paid("pay-sint-100")).isEqualTo(8500L);

        JsonNode overlap = preview(HEADER + "2026-10-01,pay-sint-100,SETTLEMENT,order-sint-100,,85.00,,90.00,5.00,BRL,mp-conta-sintetica\n");
        JsonNode overlapResult = confirm(overlap, "confirm-sint-029-b", "");
        assertThat(overlapResult.get("created").asInt()).isZero();
        assertThat(overlapResult.get("unchanged").asInt()).isEqualTo(1);
        assertThat(countLines()).isEqualTo(7);

        JsonNode enrich = preview(HEADER + "2026-10-01,pay-sint-100,SETTLEMENT,order-sint-100,Venda preenchida,85.00,,90.00,5.00,BRL,mp-conta-sintetica\n");
        JsonNode enrichResult = confirm(enrich, "confirm-sint-029-c", "");
        assertThat(enrichResult.get("enriched").asInt()).isEqualTo(1);
        assertThat(countLines()).isEqualTo(7);
        assertThat(find(lines(""), "pay-sint-100", "SETTLEMENT").get("description").asText()).isEqualTo("Venda preenchida");

        JsonNode conflict = preview(HEADER + "2026-10-01,pay-sint-100,SETTLEMENT,order-sint-100,Outro valor,10.00,,10.00,0.00,BRL,mp-conta-sintetica\n");
        assertThat(conflict.get("rows").get(0).get("eligible").asBoolean()).isFalse();
        assertThat(conflict.get("issues").toString()).contains("IDENTITY_INSUFFICIENT");
        mockMvc.perform(post("/api/v1/statement-previews/" + conflict.get("id").asText() + "/confirm")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .header("Authorization", "Bearer " + OPERATOR)
                        .header("Idempotency-Key", "confirm-sint-029-d")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(mapper.writeValueAsString(java.util.Map.of(
                                "previewToken", conflict.get("previewToken").asText(),
                                "lineNumbers", List.of(2),
                                "accountEvidence", ""))))
                .andExpect(status().isBadRequest());
        assertThat(find(lines(""), "pay-sint-100", "SETTLEMENT").get("netMinor").asLong()).isEqualTo(8500L);

        JsonNode stale = preview(HEADER + "2026-10-09,pay-sint-novo,SETTLEMENT,order-sint-novo,,20.00,,20.00,,BRL,mp-conta-sintetica\n");
        mockMvc.perform(post("/api/v1/statement-previews/" + stale.get("id").asText() + "/confirm")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .header("Authorization", "Bearer " + OPERATOR)
                        .header("Idempotency-Key", "confirm-sint-029-e")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"previewToken":"%s","lineNumbers":[2],"accountEvidence":""}
                                """.formatted("0".repeat(64))))
                .andExpect(status().isConflict());
        assertThat(countLines()).isEqualTo(7);

        JsonNode evidence = preview("""
                DATE,SOURCE_ID,RECORD_TYPE,DESCRIPTION,NET_CREDIT_AMOUNT,CURRENCY
                2026-10-07,pay-sint-evidencia,SETTLEMENT,Com evidencia,15.00,BRL
                """);
        assertThat(evidence.get("accountEvidenceRequired").asBoolean()).isTrue();
        mockMvc.perform(post("/api/v1/statement-previews/" + evidence.get("id").asText() + "/confirm")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .header("Authorization", "Bearer " + OPERATOR)
                        .header("Idempotency-Key", "confirm-sint-029-f")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"previewToken":"%s","lineNumbers":[2],"accountEvidence":"curta"}
                                """.formatted(evidence.get("previewToken").asText())))
                .andExpect(status().isBadRequest());
        JsonNode declared = confirm(evidence, "confirm-sint-029-g", "arquivo entregue pelo laboratorio");
        assertThat(declared.get("accountAttestation").asText()).isEqualTo("OPERATOR_DECLARATION");
        assertThat(countLines()).isEqualTo(8);

        JsonNode wrong = preview("DATE;SOURCE_ID;RECORD_TYPE\n2026-10-01;pay-sint-x;SETTLEMENT\n");
        assertThat(wrong.get("recognized").asBoolean()).isFalse();
        assertThat(wrong.get("fileDiagnostic").asText()).contains("vírgula");
        assertThat(countLines()).isEqualTo(8);

        JsonNode noCurrency = preview("""
                DATE,SOURCE_ID,RECORD_TYPE,NET_CREDIT_AMOUNT,ACCOUNT_EXTERNAL_REF
                2026-10-10,pay-sint-sem-moeda,SETTLEMENT,10.00,mp-conta-sintetica
                """);
        assertThat(noCurrency.get("currencyAssumed").asBoolean()).isTrue();
        assertThat(noCurrency.get("confirmBlocked").asBoolean()).isTrue();
        assertThat(noCurrency.get("fileDiagnostic").asText()).contains("Nenhuma moeda foi presumida");
        mockMvc.perform(post("/api/v1/statement-previews/" + noCurrency.get("id").asText() + "/confirm")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .header("Authorization", "Bearer " + OPERATOR)
                        .header("Idempotency-Key", "confirm-sint-030-moeda")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(mapper.writeValueAsString(java.util.Map.of(
                                "previewToken", noCurrency.get("previewToken").asText(),
                                "lineNumbers", List.of(2),
                                "accountEvidence", ""))))
                .andExpect(status().isBadRequest());
        assertThat(countLines()).isEqualTo(8);

        JsonNode refunds = preview(HEADER + """
                2026-10-11,pay-sint-estorno,REFUND,order-sint-estorno,Estorno parcial um,,10.00,10.00,,BRL,mp-conta-sintetica
                2026-10-11,pay-sint-estorno,REFUND,order-sint-estorno,Estorno parcial dois,,4.00,4.00,,BRL,mp-conta-sintetica
                """);
        assertThat(refunds.get("rows")).hasSize(2);
        assertThat(refunds.get("rows").get(0).get("eligible").asBoolean()).isFalse();
        assertThat(refunds.get("rows").get(1).get("eligible").asBoolean()).isFalse();
        assertThat(refunds.get("issues").toString()).contains("não distingue");
        assertThat(countLines()).isEqualTo(8);

        JsonNode otherAccount = preview(HEADER + "2026-10-12,pay-sint-outra,SETTLEMENT,order-sint-outra,,10.00,,10.00,,BRL,mp-outra-conta\n");
        assertThat(otherAccount.get("confirmBlocked").asBoolean()).isTrue();
        assertThat(otherAccount.get("blockReason").asText()).contains("não é a referência vinculada");
        mockMvc.perform(post("/api/v1/statement-previews/" + otherAccount.get("id").asText() + "/confirm")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .header("Authorization", "Bearer " + OPERATOR)
                        .header("Idempotency-Key", "confirm-sint-030-conta")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(mapper.writeValueAsString(java.util.Map.of(
                                "previewToken", otherAccount.get("previewToken").asText(),
                                "lineNumbers", List.of(2),
                                "accountEvidence", ""))))
                .andExpect(status().isBadRequest());

        JsonNode composition = confirm(preview(HEADER + "2026-10-12,pay-sint-composicao,SETTLEMENT,order-sint-composicao,Composicao diferente,80.00,,100.00,5.00,BRL,mp-conta-sintetica\n"), "confirm-sint-030-comp", "");
        assertThat(composition.get("created").asInt()).isEqualTo(1);
        JsonNode composed = find(lines(""), "pay-sint-composicao", "SETTLEMENT");
        assertThat(composed.get("grossMinor").asLong()).isEqualTo(10000L);
        assertThat(composed.get("feeMinor").asLong()).isEqualTo(500L);
        assertThat(composed.get("netMinor").asLong()).isEqualTo(8000L);
        assertThat(countLines()).isEqualTo(9);

        String eventKey = jdbc.queryForObject(
                "select event_key from actionfinance.statement_line where company_id = ? and source_id = 'pay-sint-100' and record_type = 'SETTLEMENT'",
                String.class,
                DemoPrincipalCatalog.COMPANY_A);
        assertThat(eventKey).isEqualTo("MERCADOPAGO|mp-account-money-csv-1|pay-sint-100|SETTLEMENT");
        assertThat(eventKey).doesNotContain("|1|");

        mockMvc.perform(get("/api/v1/statement-lines")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .header("Authorization", "Bearer " + VIEWER_B))
                .andExpect(status().isForbidden());
        mockMvc.perform(multipart("/api/v1/statement-previews")
                        .file(new MockMultipartFile("file", "extrato.csv", "text/csv", mainFile().getBytes(StandardCharsets.UTF_8)))
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .param("accountId", LocalDemoSeed.ACCOUNT_A_BANK.toString())
                        .header("Authorization", "Bearer " + VIEWER))
                .andExpect(status().isForbidden());

        assertThat(count("financial_title")).isEqualTo(titles);
        assertThat(count("settlement")).isEqualTo(settlements);
        assertThat(count("cash_movement")).isEqualTo(movements);
        assertThat(paid("pay-sint-100")).isEqualTo(8500L);
    }

    private JsonNode preview(String csv) throws Exception {
        MvcResult result = mockMvc.perform(multipart("/api/v1/statement-previews")
                        .file(new MockMultipartFile("file", "extrato.csv", "text/csv", csv.getBytes(StandardCharsets.UTF_8)))
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .param("accountId", LocalDemoSeed.ACCOUNT_A_BANK.toString())
                        .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andReturn();
        return mapper.readTree(result.getResponse().getContentAsString());
    }

    private JsonNode confirm(JsonNode preview, String key, String evidence) throws Exception {
        List<Integer> lines = new ArrayList<>();
        for (JsonNode row : preview.get("rows")) {
            if (row.get("eligible").asBoolean()) {
                lines.add(row.get("lineNumber").asInt());
            }
        }
        MvcResult result = mockMvc.perform(post("/api/v1/statement-previews/" + preview.get("id").asText() + "/confirm")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .header("Authorization", "Bearer " + OPERATOR)
                        .header("Idempotency-Key", key)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(mapper.writeValueAsString(java.util.Map.of(
                                "previewToken", preview.get("previewToken").asText(),
                                "lineNumbers", lines,
                                "accountEvidence", evidence))))
                .andExpect(status().isOk())
                .andReturn();
        return mapper.readTree(result.getResponse().getContentAsString());
    }

    private JsonNode lines(String extra) throws Exception {
        MvcResult result = mockMvc.perform(get("/api/v1/statement-lines")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .param("accountId", LocalDemoSeed.ACCOUNT_A_BANK.toString())
                        .param("size", "50")
                        .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andReturn();
        return mapper.readTree(result.getResponse().getContentAsString());
    }

    private JsonNode find(JsonNode page, String sourceId, String recordType) {
        for (JsonNode item : page.get("items")) {
            if (sourceId.equals(item.get("sourceId").asText()) && recordType.equals(item.get("recordType").asText())) {
                return item;
            }
        }
        throw new AssertionError("Linha ausente: " + sourceId + " " + recordType);
    }

    private void insertReceipt(UUID runId, String transactionId, String orderReference, String processor, long charged, long paid, String updatedAt) {
        jdbc.update(
                """
                insert into actionfinance.pay_receipt_transaction (
                    id, tenant_id, company_id, origin_system, environment, transaction_id, order_reference,
                    processor_reference, normalized_status, amount_minor, currency, amount_absent, review_required,
                    test_labeled, origin_updated_at, last_sync_run_id, created_at, updated_at, classification,
                    paid_amount_minor, paid_amount_absent
                ) values (
                    ?, ?, ?, 'ACTIONHUB_PAY', 'HOMOLOG', ?, ?, ?, 'CONFIRMED', ?, 'BRL', false, false,
                    false, ?, ?, now(), now(), 'INDETERMINATE', ?, false
                )
                """,
                UUID.randomUUID(), DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, transactionId, orderReference,
                processor, charged, OffsetDateTime.parse(updatedAt), runId, paid);
    }

    private long paid(String processor) {
        Number value = jdbc.queryForObject(
                "select paid_amount_minor from actionfinance.pay_receipt_transaction where processor_reference = ?",
                Number.class,
                processor);
        return value.longValue();
    }

    private int countLines() {
        return jdbc.queryForObject(
                "select count(*) from actionfinance.statement_line where company_id = ?",
                Integer.class,
                DemoPrincipalCatalog.COMPANY_A);
    }

    private int count(String table) {
        return jdbc.queryForObject("select count(*) from actionfinance." + table, Integer.class);
    }

    private static String mainFile() {
        return HEADER + """
                2026-10-01,pay-sint-100,SETTLEMENT,order-sint-100,,85.00,,90.00,5.00,BRL,mp-conta-sintetica
                2026-10-01,pay-sint-100,RELEASE,order-sint-100,Liberacao sintetica,90.00,,,,BRL,mp-conta-sintetica
                2026-10-02,pay-sint-201,FEE,,Tarifa avulsa,,3.50,,,BRL,mp-conta-sintetica
                2026-10-03,pay-sint-fraco,SETTLEMENT,,Sugestao fraca,12.00,,,,BRL,mp-conta-sintetica
                2026-10-04,pay-sint-falso,SETTLEMENT,,Falso candidato,40.00,,,,BRL,mp-conta-sintetica
                2026-10-05,pay-sint-ausente,SETTLEMENT,,Valor ausente,,,,,BRL,mp-conta-sintetica
                2026-10-01,pay-sint-outro,SETTLEMENT,order-sint-outro,,85.00,,90.00,5.00,BRL,mp-conta-sintetica
                2026-10-09,pay-sint-pedido,SETTLEMENT,,Nao e o pedido,1.00,,,,BRL,mp-conta-sintetica
                2026-10-05,,SETTLEMENT,,Sem identidade,10.00,,,,BRL,mp-conta-sintetica
                2026-10-05,pay-sint-usd,SETTLEMENT,,Outra moeda,10.00,,,,USD,mp-conta-sintetica
                2026-10-01,pay-sint-100,SETTLEMENT,order-sint-100,,85.00,,90.00,5.00,BRL,mp-conta-sintetica
                """;
    }
}
