package br.com.actionfinance;

import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.application.finance.LocalDemoSeed;
import br.com.actionfinance.support.PostgresFoundationContainer;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
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

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Date;
import java.sql.Timestamp;
import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
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
class ClassificationIT {

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
    void classifiesAndReconcilesWithoutTouchingTheBook() throws Exception {
        link(LocalDemoSeed.ACCOUNT_A_BANK, "mp-conta-cls-049");
        JsonNode preview = preview(accountFile(), LocalDemoSeed.ACCOUNT_A_BANK);
        JsonNode confirmed = confirm(preview, "confirm-cls-049-a", LocalDemoSeed.ACCOUNT_A_BANK);
        assertThat(confirmed.get("created").asInt()).isEqualTo(8);

        UUID alfa = initiative("ALFA", "Ensaio Alfa");
        UUID beta = initiative("BETA", "Ensaio Beta");
        JsonNode rule = rule("Meio a meio ensaio", "2026-10-01", alfa, beta, 5000, 5000);
        UUID versionId = UUID.fromString(rule.get("versionId").asText());

        UUID rateio = lineId("pay-cls-1001");
        MvcResult rejected = classifyRaw(false, List.of(rateio), 0, LocalDemoSeed.CAT_INSUMOS, "SINGLE", null, null, "key-cls-incomp-1");
        assertThat(rejected.getResponse().getStatus()).isEqualTo(400);
        assertThat(rejected.getResponse().getContentAsString()).contains("não combina");

        JsonNode previewRateio = classify(true, List.of(rateio), 0, LocalDemoSeed.CAT_VENDA, "ALLOCATED", null, versionId, "key-cls-prev-1");
        assertThat(previewRateio.get("applicable").asInt()).isEqualTo(1);
        assertThat(count("statement_decision")).isZero();
        classify(false, List.of(rateio), 0, LocalDemoSeed.CAT_VENDA, "ALLOCATED", null, versionId, "key-cls-rateio-1");
        assertThat(share(rateio, "ALFA")).isEqualByComparingTo("501");
        assertThat(share(rateio, "BETA")).isEqualByComparingTo("500");

        JsonNode future = rule("Fora da vigência", "2026-12-01", alfa, beta, 5000, 5000);
        JsonNode outside = classify(true, List.of(rateio), 1, null, "ALLOCATED", null, UUID.fromString(future.get("versionId").asText()), "key-cls-fora-1");
        assertThat(outside.get("applicable").asInt()).isZero();
        assertThat(outside.get("skipped").toString()).contains("não vale");
        assertThat(share(rateio, "ALFA")).isEqualByComparingTo("501");

        JsonNode next = postJson("/api/v1/catalogs/allocation-rules/" + rule.get("id").asText() + "/versions", "key-cls-ver-2", """
                {"name":"Nova","validFrom":"2026-10-01","shares":[
                  {"initiativeId":"%s","code":"ALFA","basisPoints":7000},
                  {"initiativeId":"%s","code":"BETA","basisPoints":3000}]}
                """.formatted(alfa, beta));
        assertThat(next.get("recalculated").asBoolean()).isFalse();
        assertThat(share(rateio, "ALFA")).isEqualByComparingTo("501");
        assertThat(share(rateio, "BETA")).isEqualByComparingTo("500");

        JsonNode page0 = queue(LocalDemoSeed.ACCOUNT_A_BANK, 0, 2);
        JsonNode page1 = queue(LocalDemoSeed.ACCOUNT_A_BANK, 1, 2);
        assertThat(page0.get("items")).isNotEmpty();
        assertThat(page1.get("items")).isNotEmpty();
        UUID first = inbound(page0, rateio, null);
        UUID second = inbound(page1, rateio, first);
        JsonNode batch = classify(false, List.of(first, second), 0, LocalDemoSeed.CAT_VENDA, "SINGLE", alfa, null, "key-cls-lote-1");
        assertThat(batch.get("saved").asInt()).isEqualTo(2);
        MvcResult conflict = classifyRaw(false, List.of(first), 0, LocalDemoSeed.CAT_VENDA, "SINGLE", alfa, null, "key-cls-lote-2");
        assertThat(conflict.getResponse().getStatus()).isEqualTo(409);
        assertThat(decisionVersion(first)).isEqualTo(1);

        int titles = count("financial_title");
        int settlements = count("settlement");
        int movements = count("cash_movement");
        BigDecimal titleSum = sum("financial_title", "amount_minor");
        BigDecimal settlementSum = sum("settlement", "amount_minor");
        BigDecimal movementSum = sum("cash_movement", "signed_amount_minor");
        UUID titleId = openTitle();
        link(LocalDemoSeed.ACCOUNT_A_CASH, "usr-sanitizado-032");
        JsonNode bookPreview = preview(releasedFile(), LocalDemoSeed.ACCOUNT_A_CASH);
        assertThat(eligible(bookPreview)).isEqualTo(3);
        confirm(bookPreview, "confirm-cls-049-livro", LocalDemoSeed.ACCOUNT_A_CASH);
        UUID credit = movement(LocalDemoSeed.ACCOUNT_A_CASH, 9000, "Crédito sintético de ensaio");
        UUID fee = movement(LocalDemoSeed.ACCOUNT_A_CASH, -500, "Tarifa sintética de ensaio");
        UUID exactMovement = movement(LocalDemoSeed.ACCOUNT_A_CASH, 2000, "Crédito exato de ensaio");
        UUID partialMovement = movement(LocalDemoSeed.ACCOUNT_A_CASH, 3000, "Crédito parcial de ensaio");
        UUID withdrawMovement = movement(LocalDemoSeed.ACCOUNT_A_CASH, 1500, "Crédito para retirada de ensaio");
        int titlesAfterFixture = count("financial_title");
        int settlementsAfterFixture = count("settlement");
        int movementsAfterFixture = count("cash_movement");
        assertThat(titlesAfterFixture).isEqualTo(titles + 1);
        assertThat(settlementsAfterFixture).isEqualTo(settlements + 5);
        assertThat(movementsAfterFixture).isEqualTo(movements + 5);

        UUID ninety = lineId("pay-livro-90");
        JsonNode reference = postJson("/api/v1/reconciliation/references", "key-cls-ref-1", """
                {"lineId":"%s","targetKind":"TITLE","titleId":"%s","comparedBasis":"GROSS","allocatedMinor":9000}
                """.formatted(ninety, titleId));
        assertThat(reference.get("bookReconciled").asBoolean()).isFalse();
        assertThat(reference.get("titleStatusUnchanged").asBoolean()).isTrue();
        assertThat(titleStatus(titleId)).isEqualTo("OPEN");
        assertThat(situation(ninety, LocalDemoSeed.ACCOUNT_A_CASH)).isEqualTo("REFERENCIA");

        JsonNode ignored = postJson("/api/v1/reconciliation/book", "key-cls-book-ignore", """
                {"lineId":"%s","allowPartial":true,"components":[{"movementId":"%s","allocatedMinor":8500}]}
                """.formatted(ninety, credit));
        assertThat(ignored.get("fullyReconciled").asBoolean()).isFalse();
        assertThat(situation(ninety, LocalDemoSeed.ACCOUNT_A_CASH)).isEqualTo("DIVERGENCIA");
        postJson("/api/v1/reconciliation/undo", "key-cls-undo-ignore", """
                {"kind":"BOOK","id":"%s","version":0,"reason":"A diferença de tarifa ficou de fora."}
                """.formatted(ignored.get("ids").get(0).asText()));
        assertThat(situation(ninety, LocalDemoSeed.ACCOUNT_A_CASH)).isEqualTo("REFERENCIA");

        JsonNode grouped = postJson("/api/v1/reconciliation/book", "key-cls-book-group", """
                {"lineId":"%s","allowPartial":false,"components":[
                  {"movementId":"%s","allocatedMinor":9000},
                  {"movementId":"%s","allocatedMinor":500}]}
                """.formatted(ninety, credit, fee));
        assertThat(grouped.get("fullyReconciled").asBoolean()).isTrue();
        assertThat(grouped.get("equation").asText()).contains("9000").contains("500");
        assertThat(situation(ninety, LocalDemoSeed.ACCOUNT_A_CASH)).isEqualTo("CONCILIADO");

        UUID exact = lineId("pay-livro-exact");
        JsonNode exactBook = postJson("/api/v1/reconciliation/book", "key-cls-book-exact", """
                {"lineId":"%s","allowPartial":false,"components":[{"movementId":"%s","allocatedMinor":2000}]}
                """.formatted(exact, exactMovement));
        assertThat(exactBook.get("fullyReconciled").asBoolean()).isTrue();
        assertThat(situation(exact, LocalDemoSeed.ACCOUNT_A_CASH)).isEqualTo("CONCILIADO");

        UUID partial = lineId("pay-livro-partial");
        JsonNode partialBook = postJson("/api/v1/reconciliation/book", "key-cls-book-partial", """
                {"lineId":"%s","allowPartial":true,"components":[{"movementId":"%s","allocatedMinor":1000}]}
                """.formatted(partial, partialMovement));
        assertThat(partialBook.get("fullyReconciled").asBoolean()).isFalse();
        assertThat(situation(partial, LocalDemoSeed.ACCOUNT_A_CASH)).isEqualTo("PARCIAL");
        MvcResult exceeded = postRaw("/api/v1/reconciliation/book", "key-cls-book-over", """
                {"lineId":"%s","allowPartial":true,"components":[{"movementId":"%s","allocatedMinor":2500}]}
                """.formatted(partial, partialMovement));
        assertThat(exceeded.getResponse().getStatus()).isEqualTo(400);
        assertThat(situation(partial, LocalDemoSeed.ACCOUNT_A_CASH)).isEqualTo("PARCIAL");

        postJson("/api/v1/reconciliation/undo", "key-cls-undo-exact", """
                {"kind":"BOOK","id":"%s","version":0,"reason":"Ensaio de desfazer a conciliação."}
                """.formatted(exactBook.get("ids").get(0).asText()));
        assertThat(situation(exact, LocalDemoSeed.ACCOUNT_A_CASH)).isEqualTo("SEM_CORRESPONDENCIA");
        JsonNode exactAgain = postJson("/api/v1/reconciliation/book", "key-cls-book-exact-2", """
                {"lineId":"%s","allowPartial":false,"components":[{"movementId":"%s","allocatedMinor":2000}]}
                """.formatted(exact, exactMovement));
        UUID exactSettlement = settlementOf(exactMovement);
        jdbc.update(
                """
                insert into actionfinance.settlement_reversal (
                    id, tenant_id, company_id, settlement_id, effective_date, reason, recorded_at, recorded_by, actor_display_name
                ) values (?,?,?,?,?,?,?,?,?)
                """,
                UUID.randomUUID(), DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, exactSettlement,
                Date.valueOf(LocalDate.of(2026, 10, 16)), "Estorno sintético posterior",
                Timestamp.from(Instant.parse("2026-10-16T15:00:00Z")), DemoPrincipalCatalog.OPERATOR_A, "Ensaio");
        assertThat(bookStatus(UUID.fromString(exactAgain.get("ids").get(0).asText()))).isEqualTo("INVALID");

        JsonNode withdrawPreview = preview(header() + releasedRow("2026-10-12T10:00:00.000-03:00", "pay-livro-retirada", "15.00", "0.00", "15.00", "0.00"), LocalDemoSeed.ACCOUNT_A_CASH);
        JsonNode withdrawConfirmed = confirm(withdrawPreview, "confirm-cls-049-w", LocalDemoSeed.ACCOUNT_A_CASH);
        UUID withdrawn = lineId("pay-livro-retirada");
        JsonNode withdrawBook = postJson("/api/v1/reconciliation/book", "key-cls-book-w", """
                {"lineId":"%s","allowPartial":false,"components":[{"movementId":"%s","allocatedMinor":1500}]}
                """.formatted(withdrawn, withdrawMovement));
        mockMvc.perform(post("/api/v1/statement-batches/" + withdrawConfirmed.get("batchId").asText() + "/withdraw")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .header("Authorization", "Bearer " + OPERATOR)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"reason\":\"Fonte retirada no ensaio.\"}"))
                .andExpect(status().isOk());
        assertThat(bookStatus(UUID.fromString(withdrawBook.get("ids").get(0).asText()))).isEqualTo("INVALID");
        assertThat(share(rateio, "ALFA")).isEqualByComparingTo("501");

        JsonNode overlap = preview(HEADER + "2026-10-02,pay-cls-1001,SETTLEMENT,ref-1001,Rateio repetido,10.01,,10.01,0.00,BRL,mp-conta-cls-049\n", LocalDemoSeed.ACCOUNT_A_BANK);
        JsonNode overlapResult = confirm(overlap, "confirm-cls-049-b", LocalDemoSeed.ACCOUNT_A_BANK);
        assertThat(overlapResult.get("created").asInt()).isZero();
        assertThat(jdbc.queryForObject(
                "select count(*) from actionfinance.statement_decision where line_id = ?",
                Integer.class, rateio)).isEqualTo(1);

        byte[] report = Files.readAllBytes(Path.of("src", "test", "resources", "statement", "settlement-v2-sanitizado-022.csv"));
        JsonNode reportPreview = preview(report, LocalDemoSeed.ACCOUNT_A_CASH);
        assertThat(reportPreview.get("rows")).hasSize(22);
        assertThat(eligible(reportPreview)).isEqualTo(4);
        Set<String> keys = eligibleKeys(reportPreview);
        JsonNode reportConfirmed = confirm(reportPreview, "confirm-cls-049-022", LocalDemoSeed.ACCOUNT_A_CASH);
        assertThat(reportConfirmed.get("created").asInt()).isEqualTo(keys.size());
        assertThat(reportConfirmed.get("inReview").asInt()).isEqualTo(18);
        assertThat(jdbc.queryForObject(
                """
                select count(*) from actionfinance.statement_occurrence
                 where batch_id = ? and consolidation = 'IN_REVIEW'
                """,
                Integer.class, UUID.fromString(reportPreview.get("id").asText()))).isEqualTo(18);

        mockMvc.perform(post("/api/v1/catalogs/initiatives")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .header("Authorization", "Bearer " + VIEWER)
                        .header("Idempotency-Key", "key-cls-viewer")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"code\":\"LEITOR\",\"name\":\"Não deve gravar\"}"))
                .andExpect(status().isForbidden());
        mockMvc.perform(get("/api/v1/reconciliation")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_B.toString())
                        .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isForbidden());
        mockMvc.perform(get("/api/v1/reconciliation/search")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .param("q", "Ensaio")
                        .header("Authorization", "Bearer " + VIEWER_B))
                .andExpect(status().isForbidden());

        assertThat(count("financial_title")).isEqualTo(titlesAfterFixture);
        assertThat(count("settlement")).isEqualTo(settlementsAfterFixture);
        assertThat(count("cash_movement")).isEqualTo(movementsAfterFixture);
        assertThat(sum("financial_title", "amount_minor")).isEqualByComparingTo(titleSum.add(new BigDecimal("9000")));
        assertThat(sum("settlement", "amount_minor")).isEqualByComparingTo(settlementSum.add(new BigDecimal("16000")));
        assertThat(sum("cash_movement", "signed_amount_minor")).isEqualByComparingTo(movementSum.add(new BigDecimal("15000")));
    }

    private String releasedFile() {
        return header()
                + releasedRow("2026-10-03T10:00:00.000-03:00", "pay-livro-90", "90.00", "-5.00", "85.00", "-5.00")
                + releasedRow("2026-10-04T10:00:00.000-03:00", "pay-livro-exact", "20.00", "0.00", "20.00", "0.00")
                + releasedRow("2026-10-05T10:00:00.000-03:00", "pay-livro-partial", "30.00", "0.00", "30.00", "0.00");
    }

    private static String header() {
        return """
                TRANSACTION_DATE;SETTLEMENT_DATE;SOURCE_ID;PAYMENT_METHOD_TYPE;TRANSACTION_TYPE;TRANSACTION_AMOUNT;FEE_AMOUNT;REAL_AMOUNT;TAXES_AMOUNT;BUSINESS_UNIT;SUB_UNIT;MONEY_RELEASE_DATE;EXTERNAL_REFERENCE;USER_ID;PAYMENT_METHOD;SITE;TRANSACTION_CURRENCY;SETTLEMENT_NET_AMOUNT;SETTLEMENT_CURRENCY;COUPON_AMOUNT;MKP_FEE_AMOUNT;FINANCING_FEE_AMOUNT;SHIPPING_FEE_AMOUNT;SELLER_AMOUNT;INSTALLMENTS;INSTALLMENT_NUMBER;INSTALLMENT_NET_AMOUNT;IS_RELEASED;DESCRIPTION;METADATA;OPERATION_TAGS;SALE_DETAIL;PRODUCT_SKU;TRANSACTION_INTENT_ID;ORDER_MP;ORDER_ID;PURCHASE_ID;APPLICATION_ID;STORE_ID;STORE_NAME;EXTERNAL_STORE_ID;TAX_DETAIL;TAXES_DISAGGREGATED;POI_WALLET_NAME;POI_BANK_NAME;INVOICING_PERIOD
                """;
    }

    private static String releasedRow(String when, String sourceId, String gross, String fee, String net, String mkp) {
        String sample = "2026-10-06T10:00:00.000-03:00;2026-10-06T10:00:00.000-03:00;pay-san-01;bank_transfer;SETTLEMENT;100.00;0.00;100.00;0.00;Mercado Pago;Checkouts;2026-10-06T10:00:00.000-03:00;;usr-sanitizado-032;pix;MLB;BRL;100.00;BRL;0.00;0.00;0.00;0.00;0.00;1;;;true;;[{}];[\"PIX\"];;;;;;;;;;;;;;;";
        return sample.replace("2026-10-06T10:00:00.000-03:00", when)
                .replace("pay-san-01", sourceId)
                .replace(";100.00;0.00;100.00;0.00;", ";" + gross + ";" + fee + ";" + net + ";0.00;")
                .replace(";BRL;100.00;BRL;0.00;0.00;0.00;0.00;0.00;", ";BRL;" + net + ";BRL;0.00;" + mkp + ";0.00;0.00;" + net + ";")
                + "\n";
    }

    private String accountFile() {
        return HEADER + """
                2026-10-02,pay-cls-1001,SETTLEMENT,ref-1001,Rateio de ensaio,10.01,,10.01,0.00,BRL,mp-conta-cls-049
                2026-10-03,pay-cls-90,SETTLEMENT,ref-90,Recebimento com tarifa,85.00,,90.00,5.00,BRL,mp-conta-cls-049
                2026-10-04,pay-cls-exact,SETTLEMENT,ref-exact,Recebimento exato,20.00,,20.00,0.00,BRL,mp-conta-cls-049
                2026-10-05,pay-cls-partial,SETTLEMENT,ref-partial,Recebimento parcial,30.00,,30.00,0.00,BRL,mp-conta-cls-049
                2026-10-06,pay-cls-p1,SETTLEMENT,ref-p1,Página um,1.00,,1.00,0.00,BRL,mp-conta-cls-049
                2026-10-07,pay-cls-p2,SETTLEMENT,ref-p2,Página dois,1.00,,1.00,0.00,BRL,mp-conta-cls-049
                2026-10-08,pay-cls-p3,SETTLEMENT,ref-p3,Página três,1.00,,1.00,0.00,BRL,mp-conta-cls-049
                2026-10-09,pay-cls-out,PAYOUT,ref-out,Saída de ensaio,,15.00,15.00,0.00,BRL,mp-conta-cls-049
                """;
    }

    private void link(UUID accountId, String ref) throws Exception {
        mockMvc.perform(post("/api/v1/statement-links")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .header("Authorization", "Bearer " + OPERATOR)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"accountId":"%s","externalRef":"%s","provenance":"vinculo sintetico de laboratorio"}
                                """.formatted(accountId, ref)))
                .andExpect(status().isOk());
    }

    private JsonNode preview(String csv, UUID accountId) throws Exception {
        return preview(csv.getBytes(StandardCharsets.UTF_8), accountId);
    }

    private JsonNode preview(byte[] csv, UUID accountId) throws Exception {
        MvcResult result = mockMvc.perform(multipart("/api/v1/statement-previews")
                        .file(new MockMultipartFile("file", "extrato.csv", "text/csv", csv))
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .param("accountId", accountId.toString())
                        .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andReturn();
        return mapper.readTree(result.getResponse().getContentAsString());
    }

    private JsonNode confirm(JsonNode preview, String key, UUID accountId) throws Exception {
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
                                "accountEvidence", ""))))
                .andExpect(status().isOk())
                .andReturn();
        JsonNode body = mapper.readTree(result.getResponse().getContentAsString());
        if (body.get("batchId") == null && body.isObject()) {
            ((ObjectNode) body).put("batchId", preview.get("id").asText());
        }
        return body;
    }

    private UUID initiative(String code, String name) throws Exception {
        return UUID.fromString(postJson("/api/v1/catalogs/initiatives", "key-cls-ini-" + code, """
                {"code":"%s","name":"%s"}
                """.formatted(code, name)).get("id").asText());
    }

    private JsonNode rule(String name, String from, UUID alfa, UUID beta, int left, int right) throws Exception {
        return postJson("/api/v1/catalogs/allocation-rules", "key-cls-rule-" + from + left, """
                {"name":"%s","validFrom":"%s","shares":[
                  {"initiativeId":"%s","code":"ALFA","basisPoints":%d},
                  {"initiativeId":"%s","code":"BETA","basisPoints":%d}]}
                """.formatted(name, from, alfa, left, beta, right));
    }

    private JsonNode classify(boolean preview, List<UUID> ids, long version, UUID category, String assignment, UUID initiative, UUID ruleVersion, String key) throws Exception {
        MvcResult result = classifyRaw(preview, ids, version, category, assignment, initiative, ruleVersion, key);
        if (result.getResponse().getStatus() != 200) {
            return null;
        }
        return mapper.readTree(result.getResponse().getContentAsString());
    }

    private MvcResult classifyRaw(boolean preview, List<UUID> ids, long version, UUID category, String assignment, UUID initiative, UUID ruleVersion, String key) throws Exception {
        ObjectNode body = mapper.createObjectNode();
        body.put("preview", preview);
        body.putArray("lineIds");
        var versions = body.putObject("versions");
        for (UUID id : ids) {
            body.withArray("lineIds").add(id.toString());
            versions.put(id.toString(), version);
        }
        if (category != null) {
            body.put("categoryId", category.toString());
        }
        body.put("clearCategory", false);
        body.put("assignment", assignment);
        if (initiative != null) {
            body.put("initiativeId", initiative.toString());
        }
        if (ruleVersion != null) {
            body.put("ruleVersionId", ruleVersion.toString());
        }
        body.put("reason", "Decisão de ensaio.");
        return mockMvc.perform(post("/api/v1/reconciliation/classifications")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .header("Authorization", "Bearer " + OPERATOR)
                        .header("Idempotency-Key", key)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(mapper.writeValueAsString(body)))
                .andReturn();
    }

    private JsonNode postJson(String path, String key, String json) throws Exception {
        MvcResult result = postRaw(path, key, json);
        assertThat(result.getResponse().getStatus()).as(result.getResponse().getContentAsString()).isEqualTo(200);
        return mapper.readTree(result.getResponse().getContentAsString());
    }

    private MvcResult postRaw(String path, String key, String json) throws Exception {
        return mockMvc.perform(post(path)
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .header("Authorization", "Bearer " + OPERATOR)
                        .header("Idempotency-Key", key)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json))
                .andReturn();
    }

    private JsonNode queue(UUID accountId, int page, int size) throws Exception {
        MvcResult result = mockMvc.perform(get("/api/v1/reconciliation")
                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                        .param("accountId", accountId.toString())
                        .param("page", String.valueOf(page))
                        .param("size", String.valueOf(size))
                        .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andReturn();
        return mapper.readTree(result.getResponse().getContentAsString());
    }

    private static UUID inbound(JsonNode page, UUID excluded, UUID alsoExcluded) {
        for (JsonNode item : page.get("items")) {
            if (!"IN".equals(item.get("direction").asText())) {
                continue;
            }
            UUID id = UUID.fromString(item.get("lineId").asText());
            if (id.equals(excluded) || id.equals(alsoExcluded)) {
                continue;
            }
            return id;
        }
        throw new AssertionError("A página não tem uma entrada livre para o lote.");
    }

    private UUID lineId(String sourceId) {
        return jdbc.queryForObject(
                "select id from actionfinance.statement_line where company_id = ? and source_id = ?",
                UUID.class, DemoPrincipalCatalog.COMPANY_A, sourceId);
    }

    private BigDecimal share(UUID lineId, String code) {
        return jdbc.queryForObject(
                """
                select s.amount_minor
                  from actionfinance.statement_decision_share s
                  join actionfinance.statement_decision d on d.id = s.decision_id
                  join actionfinance.initiative i on i.id = s.initiative_id
                 where d.line_id = ? and i.code = ?
                """,
                BigDecimal.class, lineId, code);
    }

    private long decisionVersion(UUID lineId) {
        return jdbc.queryForObject(
                "select version from actionfinance.statement_decision where line_id = ?",
                Long.class, lineId);
    }

    private String situation(UUID lineId, UUID accountId) throws Exception {
        JsonNode page = queue(accountId, 0, 50);
        for (JsonNode item : page.get("items")) {
            if (lineId.toString().equals(item.get("lineId").asText())) {
                return item.get("situation").asText();
            }
        }
        throw new AssertionError("Movimento ausente na fila: " + lineId);
    }

    private UUID openTitle() {
        UUID id = UUID.randomUUID();
        Instant now = Instant.parse("2026-10-16T12:00:00Z");
        jdbc.update(
                """
                insert into actionfinance.financial_title (
                    id, tenant_id, company_id, reference, direction, status, description,
                    counterparty_id, category_id, amount_minor, currency, competence_date, due_date,
                    origin_kind, source_reference, version, created_at, updated_at, created_by, updated_by, confirmed_at
                ) values (?,?,?,?, 'RECEIVABLE','OPEN','Título sintético ainda aberto',?,?,?,'BRL',?,?, 'MANUAL','ensaio-049',0,?,?,?,?,?)
                """,
                id, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, "REC-ENSAIO-049",
                LocalDemoSeed.CP_PADARIA_CLIENTE, LocalDemoSeed.CAT_VENDA, new BigDecimal("9000"),
                Date.valueOf(LocalDate.of(2026, 10, 3)), Date.valueOf(LocalDate.of(2026, 10, 3)),
                Timestamp.from(now), Timestamp.from(now), DemoPrincipalCatalog.OPERATOR_A, DemoPrincipalCatalog.OPERATOR_A,
                Timestamp.from(now));
        return id;
    }

    private UUID movement(UUID accountId, long signed, String description) {
        UUID settlementId = UUID.randomUUID();
        UUID movementId = UUID.randomUUID();
        Instant now = Instant.parse("2026-10-16T12:00:00Z");
        jdbc.update(
                """
                insert into actionfinance.settlement (
                    id, tenant_id, company_id, account_id, direction, amount_minor, currency,
                    effective_date, method, note, origin_kind, recorded_at, recorded_by, actor_display_name
                ) values (?,?,?,?,?,?,'BRL',?,'PIX',?,'MANUAL',?,?,?)
                """,
                settlementId, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, accountId,
                signed < 0 ? "PAYABLE" : "RECEIVABLE", BigDecimal.valueOf(Math.abs(signed)),
                Date.valueOf(LocalDate.of(2026, 10, 3)), description,
                Timestamp.from(now), DemoPrincipalCatalog.OPERATOR_A, "Ensaio");
        jdbc.update(
                """
                insert into actionfinance.cash_movement (
                    id, tenant_id, company_id, account_id, kind, signed_amount_minor, currency,
                    effective_date, recorded_at, recorded_by, settlement_id, reversal_id, description)
                values (?,?,?,?, 'SETTLEMENT', ?, 'BRL', ?, ?, ?, ?, null, ?)
                """,
                movementId, DemoPrincipalCatalog.TENANT_A, DemoPrincipalCatalog.COMPANY_A, accountId,
                signed, Date.valueOf(LocalDate.of(2026, 10, 3)), Timestamp.from(now), DemoPrincipalCatalog.OPERATOR_A,
                settlementId, description);
        return movementId;
    }

    private UUID settlementOf(UUID movementId) {
        return jdbc.queryForObject(
                "select settlement_id from actionfinance.cash_movement where id = ?",
                UUID.class, movementId);
    }

    private String bookStatus(UUID allocationId) {
        return jdbc.queryForObject(
                "select status from actionfinance.statement_book_allocation where id = ?",
                String.class, allocationId);
    }

    private String titleStatus(UUID titleId) {
        return jdbc.queryForObject(
                "select status from actionfinance.financial_title where id = ?",
                String.class, titleId);
    }

    private int count(String table) {
        return jdbc.queryForObject("select count(*) from actionfinance." + table, Integer.class);
    }

    private BigDecimal sum(String table, String column) {
        return jdbc.queryForObject("select coalesce(sum(" + column + "), 0) from actionfinance." + table, BigDecimal.class);
    }

    private static int eligible(JsonNode preview) {
        int count = 0;
        for (JsonNode row : preview.get("rows")) {
            if (row.get("eligible").asBoolean()) {
                count++;
            }
        }
        return count;
    }

    private static Set<String> eligibleKeys(JsonNode preview) {
        Set<String> keys = new HashSet<>();
        for (JsonNode row : preview.get("rows")) {
            if (row.get("eligible").asBoolean()) {
                keys.add(row.get("eventKey").asText());
            }
        }
        return keys;
    }
}
