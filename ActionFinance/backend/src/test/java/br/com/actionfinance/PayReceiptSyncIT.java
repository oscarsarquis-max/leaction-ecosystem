package br.com.actionfinance;

import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.application.integration.PayReceiptSyncService;
import br.com.actionfinance.application.integration.SpiderInteractionClient;
import br.com.actionfinance.application.integration.SpiderInteractionClient.SpiderListResult;
import br.com.actionfinance.support.PostgresFoundationContainer;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("local-demo")
@Testcontainers
class PayReceiptSyncIT {

    private static final String OPERATOR = "operator-demo-token-aaaaaaaaaaaaaaaaaaaa";
    private static final String VIEWER = "viewer-a-demo-token-bbbbbbbbbbbbbbbbbbbb";

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
        registry.add("actionfinance.demo-auth.viewer-b-token", () -> "viewer-b-demo-token-cccccccccccccccccccc");
        registry.add("actionfinance.demo-auth.operator-multi-token", () -> "operator-multi-token-dddddddddddddddddd");
        registry.add("actionfinance.clock.zone", () -> "America/Sao_Paulo");
        registry.add("actionfinance.integration.homolog", () -> "true");
        registry.add("actionfinance.integration.sync-page-limit", () -> "2");
    }

    @Autowired
    MockMvc mockMvc;

    @Autowired
    ObjectMapper mapper;

    @Autowired
    JdbcTemplate jdbc;

    @MockBean
    SpiderInteractionClient spider;

    @BeforeEach
    void clean() {
        jdbc.update(
                "update actionfinance.pay_company_mapping set authorized = true where company_id = ?",
                DemoPrincipalCatalog.COMPANY_A);
    }

    @Test
    void firstSyncPaginatesDedupesAndUpdatesOldRowWithoutFinancialMovement() throws Exception {
        long titlesBefore = count("financial_title");
        long settlementsBefore = count("settlement");
        long movementsBefore = count("cash_movement");
        AtomicInteger calls = new AtomicInteger();
        when(spider.list(any(), any(), any(), any(), any(), anyInt()))
                .thenAnswer(
                        invocation -> {
                            int n = calls.incrementAndGet();
                            if (n == 1) {
                                return page(
                                        "c1",
                                        List.of(
                                                item("fs-pending", "PENDING", "IN_PROGRESS", "8900", "2026-10-01T10:00:00Z"),
                                                item("fs-paid", "PAID", "CONFIRMED", "12550", "2026-10-01T10:00:01Z")),
                                        "cursor-a");
                            }
                            if (n == 2) {
                                return page(
                                        "c2",
                                        List.of(
                                                item("fs-missing", "PAID", "CONFIRMED", null, "2026-10-01T10:00:02Z"),
                                                item("fs-refund", "REFUNDED", "REFUNDED", "12550", "2026-10-01T10:00:03Z")),
                                        null);
                            }
                            return page(
                                    "c3",
                                    List.of(item("fs-paid", "PAID", "CONFIRMED", "13000", "2026-10-01T11:00:00Z")),
                                    null);
                        });
        mockMvc.perform(
                        post("/api/v1/pay-receipts/sync")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.run.status").value("SUCCESS"))
                .andExpect(jsonPath("$.run.pageCount").value(2))
                .andExpect(jsonPath("$.run.importedCount").value(4));
        mockMvc.perform(
                        post("/api/v1/pay-receipts/sync")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.run.status").value("SUCCESS"));
        Integer rows =
                jdbc.queryForObject(
                        "select count(*) from actionfinance.pay_receipt_transaction where transaction_id like 'fs-%'",
                        Integer.class);
        assertThat(rows).isEqualTo(4);
        String amount =
                jdbc.queryForObject(
                        "select amount_minor::text from actionfinance.pay_receipt_transaction where transaction_id = 'fs-paid'",
                        String.class);
        assertThat(amount).isEqualTo("13000");
        String missing =
                jdbc.queryForObject(
                        "select amount_minor from actionfinance.pay_receipt_transaction where transaction_id = 'fs-missing'",
                        String.class);
        assertThat(missing).isNull();
        assertThat(count("financial_title")).isEqualTo(titlesBefore);
        assertThat(count("settlement")).isEqualTo(settlementsBefore);
        assertThat(count("cash_movement")).isEqualTo(movementsBefore);
    }

    @Test
    void failureBetweenPagesAllowsResumeWithoutLosingConfirmedPage() throws Exception {
        AtomicInteger calls = new AtomicInteger();
        when(spider.list(any(), any(), any(), any(), any(), anyInt()))
                .thenAnswer(
                        invocation -> {
                            int n = calls.incrementAndGet();
                            if (n == 1) {
                                return page(
                                        "p1",
                                        List.of(item("fb-a", "PAID", "CONFIRMED", "1000", "2026-10-01T12:00:00Z")),
                                        "cursor-keep");
                            }
                            if (n == 2) {
                                return SpiderListResult.unavailable("p2", "Spider interrompida");
                            }
                            return page(
                                    "p3",
                                    List.of(item("fb-b", "PENDING", "IN_PROGRESS", "2000", "2026-10-01T12:00:01Z")),
                                    null);
                        });
        JsonNode first =
                mapper.readTree(
                        mockMvc.perform(
                                        post("/api/v1/pay-receipts/sync")
                                                .header("Authorization", "Bearer " + OPERATOR)
                                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString()))
                                .andExpect(status().isOk())
                                .andReturn()
                                .getResponse()
                                .getContentAsString());
        assertThat(first.path("run").path("status").asText()).isEqualTo("PARTIAL");
        assertThat(first.path("run").path("importedCount").asInt()).isEqualTo(1);
        mockMvc.perform(
                        post("/api/v1/pay-receipts/sync")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.run.status").value("SUCCESS"))
                .andExpect(jsonPath("$.run.importedCount").value(1));
        Integer rows =
                jdbc.queryForObject(
                        "select count(*) from actionfinance.pay_receipt_transaction where transaction_id like 'fb-%'",
                        Integer.class);
        assertThat(rows).isEqualTo(2);
    }

    @Test
    void concurrentSyncsKeepSingleRunning() throws Exception {
        CountDownLatch started = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);
        when(spider.list(any(), any(), any(), any(), any(), anyInt()))
                .thenAnswer(
                        invocation -> {
                            started.countDown();
                            release.await();
                            return page("lock", List.of(item("cc-lock", "PAID", "CONFIRMED", "1", "2026-10-01T13:00:00Z")), null);
                        });
        var pool = Executors.newFixedThreadPool(2);
        Future<Integer> first =
                pool.submit(
                        () ->
                                mockMvc.perform(
                                                post("/api/v1/pay-receipts/sync")
                                                        .header("Authorization", "Bearer " + OPERATOR)
                                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString()))
                                        .andReturn()
                                        .getResponse()
                                        .getStatus());
        assertThat(started.await(5, java.util.concurrent.TimeUnit.SECONDS)).isTrue();
        int conflict =
                mockMvc.perform(
                                post("/api/v1/pay-receipts/sync")
                                        .header("Authorization", "Bearer " + OPERATOR)
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString()))
                        .andReturn()
                        .getResponse()
                        .getStatus();
        release.countDown();
        assertThat(first.get()).isEqualTo(200);
        assertThat(conflict).isEqualTo(409);
        pool.shutdownNow();
    }

    @Test
    void staleRunningIsReclaimedWithoutManualCleanup() throws Exception {
        jdbc.update(
                """
                insert into actionfinance.pay_receipt_sync_run (
                    id, tenant_id, company_id, origin_system, environment, status,
                    root_correlation_id, start_cursor, resume_cursor, page_count,
                    imported_count, updated_count, review_count, last_error,
                    started_at, created_at, updated_at)
                values (
                    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa09', ?, ?, 'ACTIONHUB_PAY', 'HOMOLOG',
                    'RUNNING', 'afr-orphan', null, null, 1, 1, 0, 0, null,
                    now() - interval '2 hours', now() - interval '2 hours', now() - interval '2 hours')
                """,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A);
        when(spider.list(any(), any(), any(), any(), any(), anyInt()))
                .thenReturn(page("orphan-resume", List.of(), null));
        mockMvc.perform(
                        post("/api/v1/pay-receipts/sync")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.run.status").value("EMPTY"));
        Integer orphans =
                jdbc.queryForObject(
                        """
                        select count(*) from actionfinance.pay_receipt_sync_run
                        where company_id = ? and status = 'RUNNING'
                        """,
                        Integer.class,
                        DemoPrincipalCatalog.COMPANY_A);
        assertThat(orphans).isZero();
        String previous =
                jdbc.queryForObject(
                        """
                        select status from actionfinance.pay_receipt_sync_run
                        where id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa09'
                        """,
                        String.class);
        assertThat(previous).isEqualTo("PARTIAL");
    }

    @Test
    void productionReviewsPersistWithChargedAmountAndAbsentPaidWithoutMovement() throws Exception {
        jdbc.update(
                "update actionfinance.pay_company_mapping set environment = 'PRODUCTION' where company_id = ?",
                DemoPrincipalCatalog.COMPANY_A);
        try {
        long titlesBefore = count("financial_title");
        when(spider.list(any(), any(), any(), any(), any(), anyInt()))
                .thenReturn(
                        page(
                                "rev-1",
                                List.of(),
                                List.of(
                                        review(
                                                "rv-paid",
                                                "PAID",
                                                "CONFIRMED",
                                                "7000",
                                                null,
                                                "INDETERMINATE",
                                                "2026-10-01T15:00:00Z"),
                                        review(
                                                "rv-pending",
                                                "PENDING",
                                                "IN_PROGRESS",
                                                "7000",
                                                null,
                                                "INDETERMINATE",
                                                "2026-10-01T15:00:01Z")),
                                null,
                                "PRODUCTION"));
        mockMvc.perform(
                        post("/api/v1/pay-receipts/sync")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("environment", "PRODUCTION"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.run.importedCount").value(2))
                .andExpect(jsonPath("$.reviews.length()").value(2))
                .andExpect(jsonPath("$.reviews[0].originalStatus").value("PENDING"))
                .andExpect(jsonPath("$.reviews[0].paidAmountAbsent").value(true))
                .andExpect(jsonPath("$.reviews[1].originalStatus").value("PAID"))
                .andExpect(jsonPath("$.reviews[1].amountMinor").value("7000"));
        mockMvc.perform(
                        post("/api/v1/pay-receipts/sync")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("environment", "PRODUCTION"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.run.importedCount").value(0));
        Integer rows =
                jdbc.queryForObject(
                        "select count(*) from actionfinance.pay_receipt_transaction where transaction_id like 'rv-%'",
                        Integer.class);
        assertThat(rows).isEqualTo(2);
        assertThat(count("financial_title")).isEqualTo(titlesBefore);
        } finally {
        jdbc.update(
                "update actionfinance.pay_company_mapping set environment = 'HOMOLOG' where company_id = ?",
                DemoPrincipalCatalog.COMPANY_A);
        }
    }

    @Test
    void recoversPaidPayerWithoutCopyingChargedAndKeepsExpectedUnpaid() throws Exception {
        jdbc.update(
                "update actionfinance.pay_company_mapping set environment = 'PRODUCTION' where company_id = ?",
                DemoPrincipalCatalog.COMPANY_A);
        try {
            when(spider.list(any(), any(), any(), any(), any(), anyInt()))
                    .thenReturn(
                            page(
                                    "c90",
                                    List.of(
                                            commercialItem(
                                                    "11111111-2222-4333-8444-666666666666",
                                                    "PAID",
                                                    "CONFIRMED",
                                                    "9000",
                                                    "9000",
                                                    "REAL",
                                                    "2026-10-06T17:13:33Z",
                                                    "cliente@exemplo.test",
                                                    "pix"),
                                            commercialItem(
                                                    "hist-pending-1",
                                                    "PENDING",
                                                    "IN_PROGRESS",
                                                    "7000",
                                                    null,
                                                    "REAL",
                                                    "2026-09-01T10:00:00Z",
                                                    null,
                                                    null)),
                                    List.of(),
                                    null,
                                    "PRODUCTION"));
            JsonNode body =
                    mapper.readTree(
                            mockMvc.perform(
                                            post("/api/v1/pay-receipts/sync")
                                                    .header("Authorization", "Bearer " + OPERATOR)
                                                    .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                                    .param("environment", "PRODUCTION"))
                                    .andExpect(status().isOk())
                                    .andExpect(jsonPath("$.run.importedCount").value(2))
                                    .andReturn()
                                    .getResponse()
                                    .getContentAsString());
            JsonNode paid =
                    body.path("items").get(0).path("transactionId").asText().contains("11111111-2222-4333-8444-666666666666")
                            ? body.path("items").get(0)
                            : body.path("items").get(1);
            JsonNode pending =
                    body.path("items").get(0).path("transactionId").asText().contains("hist-pending")
                            ? body.path("items").get(0)
                            : body.path("items").get(1);
            assertThat(paid.path("paidAmountMinor").asText()).isEqualTo("9000");
            assertThat(paid.path("paidAmountAbsent").asBoolean()).isFalse();
            assertThat(paid.path("payerLabel").asText()).isEqualTo("cliente@exemplo.test");
            assertThat(paid.path("payerKind").asText()).isEqualTo("EMAIL");
            assertThat(paid.path("paymentMethod").asText()).isEqualTo("pix");
            assertThat(paid.path("commercialApplication").asText()).isEqualTo("lojadepaes");
            assertThat(paid.path("pendingKind").asText()).isEqualTo("NONE");
            assertThat(pending.path("paidAmountMinor").isNull()).isTrue();
            assertThat(pending.path("pendingKind").asText()).isEqualTo("UNPAID_EXPECTED");
            mockMvc.perform(
                            post("/api/v1/pay-receipts/sync")
                                    .header("Authorization", "Bearer " + OPERATOR)
                                    .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                    .param("environment", "PRODUCTION"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.run.importedCount").value(0));
            Integer rows =
                    jdbc.queryForObject(
                            "select count(*) from actionfinance.pay_receipt_transaction where transaction_id in ('11111111-2222-4333-8444-666666666666','hist-pending-1')",
                            Integer.class);
            assertThat(rows).isEqualTo(2);
        } finally {
            jdbc.update(
                    "update actionfinance.pay_company_mapping set environment = 'HOMOLOG' where company_id = ?",
                    DemoPrincipalCatalog.COMPANY_A);
        }
    }

    @Test
    void enrichmentAtSameRevisionUpdatesWithoutErasingNewerObservation() throws Exception {
        AtomicInteger calls = new AtomicInteger();
        when(spider.list(any(), any(), any(), any(), any(), anyInt()))
                .thenAnswer(
                        invocation -> {
                            int n = calls.incrementAndGet();
                            if (n == 1) {
                                return page(
                                        "en-1",
                                        List.of(item("en-90", "PAID", "CONFIRMED", "9000", "2026-10-06T17:13:33Z")),
                                        null);
                            }
                            Map<String, Object> enriched =
                                    commercialItem(
                                            "en-90",
                                            "PAID",
                                            "CONFIRMED",
                                            "9000",
                                            "9000",
                                            "TEST",
                                            "2026-10-06T17:13:33Z",
                                            "cliente@exemplo.test",
                                            "pix");
                            if (n == 2) {
                                return page("en-2", List.of(enriched), null);
                            }
                            Map<String, Object> older = item("en-90", "PENDING", "IN_PROGRESS", "1", "2026-10-01T00:00:00Z");
                            return page("en-3", List.of(older), null);
                        });
        mockMvc.perform(
                        post("/api/v1/pay-receipts/sync")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.run.importedCount").value(1));
        mockMvc.perform(
                        post("/api/v1/pay-receipts/sync")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.run.updatedCount").value(1));
        mockMvc.perform(
                        post("/api/v1/pay-receipts/sync")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.run.updatedCount").value(0));
        String paid =
                jdbc.queryForObject(
                        "select paid_amount_minor::text from actionfinance.pay_receipt_transaction where transaction_id = 'en-90'",
                        String.class);
        String payer =
                jdbc.queryForObject(
                        "select payer_label from actionfinance.pay_receipt_transaction where transaction_id = 'en-90'",
                        String.class);
        String status =
                jdbc.queryForObject(
                        "select normalized_status from actionfinance.pay_receipt_transaction where transaction_id = 'en-90'",
                        String.class);
        assertThat(paid).isEqualTo("9000");
        assertThat(payer).isEqualTo("cliente@exemplo.test");
        assertThat(status).isEqualTo("CONFIRMED");
    }

    @Test
    void confirmedWithoutPaidIsSpecificPendingAndDoesNotCopyAmount() throws Exception {
        jdbc.update(
                "update actionfinance.pay_company_mapping set environment = 'PRODUCTION' where company_id = ?",
                DemoPrincipalCatalog.COMPANY_A);
        try {
            Map<String, Object> approved =
                    commercialItem(
                            "ap-no-paid",
                            "PAID",
                            "CONFIRMED",
                            "9000",
                            null,
                            "REAL",
                            "2026-10-06T12:00:00Z",
                            "cliente@exemplo.test",
                            "pix");
            when(spider.list(any(), any(), any(), any(), any(), anyInt()))
                    .thenReturn(page("ap-1", List.of(approved), List.of(), null, "PRODUCTION"));
            JsonNode body =
                    mapper.readTree(
                            mockMvc.perform(
                                            post("/api/v1/pay-receipts/sync")
                                                    .header("Authorization", "Bearer " + OPERATOR)
                                                    .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                                    .param("environment", "PRODUCTION"))
                                    .andExpect(status().isOk())
                                    .andReturn()
                                    .getResponse()
                                    .getContentAsString());
            JsonNode found = null;
            for (JsonNode row : body.path("items")) {
                if ("ap-no-paid".equals(row.path("transactionId").asText())) {
                    found = row;
                }
            }
            assertThat(found).isNotNull();
            assertThat(found.path("paidAmountAbsent").asBoolean()).isTrue();
            assertThat(found.path("paidAmountMinor").isMissingNode() || found.path("paidAmountMinor").isNull()).isTrue();
            assertThat(found.path("amountMinor").asText()).isEqualTo("9000");
            assertThat(found.path("pendingKind").asText()).isEqualTo("PAID_AMOUNT_MISSING");
        } finally {
            jdbc.update(
                    "update actionfinance.pay_company_mapping set environment = 'HOMOLOG' where company_id = ?",
                    DemoPrincipalCatalog.COMPANY_A);
        }
    }

    @Test
    void viewerCannotSyncAndWrongEnvironmentIsRejected() throws Exception {
        mockMvc.perform(
                        post("/api/v1/pay-receipts/sync")
                                .header("Authorization", "Bearer " + VIEWER)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString()))
                .andExpect(status().isForbidden());
        mockMvc.perform(
                        post("/api/v1/pay-receipts/sync")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("environment", "SANDBOX"))
                .andExpect(status().isBadRequest());
    }

    private long count(String table) {
        Long value =
                jdbc.queryForObject(
                        "select count(*) from actionfinance." + table + " where company_id = ?",
                        Long.class,
                        DemoPrincipalCatalog.COMPANY_A);
        return value == null ? 0 : value;
    }

    @Test
    void payerFieldsSurviveANullFollowUpOnTheMigratedSchema() throws Exception {
        List<Map<String, Object>> columns =
                jdbc.queryForList(
                        """
                        select column_name, is_nullable, column_default
                        from information_schema.columns
                        where table_schema = 'actionfinance'
                          and table_name = 'pay_receipt_transaction'
                          and column_name in (
                            'payer_name', 'payer_email', 'store_order_reference', 'store_payment_request_id',
                            'processor_payment_id', 'processor_approved_at', 'processor_installments',
                            'purchase_description')
                        """);
        assertThat(columns).hasSize(8);
        assertThat(columns).allSatisfy(
                column -> {
                    assertThat(column.get("is_nullable")).isEqualTo("YES");
                    assertThat(column.get("column_default")).isNull();
                });
        Map<String, Object> real = item("py-real", "PAID", "CONFIRMED", "9000", "2026-11-09T18:00:00Z");
        real.put("payerName", "Pagador Exemplo");
        real.put("payerEmail", "pagador.exemplo@exemplo.test");
        real.put("storeOrderReference", "PED-1042");
        real.put("storePaymentRequestId", "req-77");
        real.put("processorPaymentId", "mp-1");
        real.put("processorApprovedAt", "2026-11-09T18:04:11Z");
        real.put("processorInstallments", 2);
        real.put("purchaseDescription", "Fornada de sábado");
        Map<String, Object> technical = item("py-tech", "PAID", "CONFIRMED", "100", "2026-11-09T18:00:01Z");
        technical.put("payerEmail", "loja@amount.hub.local");
        technical.put("payerName", "");
        Map<String, Object> followUp = item("py-real", "PAID", "CONFIRMED", "9000", "2026-11-09T19:00:00Z");
        followUp.put("payerName", "");
        followUp.put("payerEmail", "loja@amount.hub.local");
        followUp.put("storeOrderReference", null);
        followUp.put("purchaseDescription", "");
        followUp.put("processorInstallments", null);
        AtomicInteger calls = new AtomicInteger();
        when(spider.list(any(), any(), any(), any(), any(), anyInt()))
                .thenAnswer(
                        invocation -> {
                            if (calls.incrementAndGet() == 1) {
                                return page("py-1", List.of(real, technical), null);
                            }
                            return page("py-2", List.of(followUp), null);
                        });
        ch.qos.logback.classic.Logger logger =
                (ch.qos.logback.classic.Logger) org.slf4j.LoggerFactory.getLogger(PayReceiptSyncService.class);
        ch.qos.logback.core.read.ListAppender<ch.qos.logback.classic.spi.ILoggingEvent> appender =
                new ch.qos.logback.core.read.ListAppender<>();
        appender.start();
        logger.addAppender(appender);
        try {
            mockMvc.perform(
                            post("/api/v1/pay-receipts/sync")
                                    .header("Authorization", "Bearer " + OPERATOR)
                                    .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString()))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.run.importedCount").value(2));
            mockMvc.perform(
                            post("/api/v1/pay-receipts/sync")
                                    .header("Authorization", "Bearer " + OPERATOR)
                                    .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString()))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.run.updatedCount").value(0));
        } finally {
            logger.detachAppender(appender);
        }
        Map<String, Object> stored =
                jdbc.queryForMap(
                        """
                        select payer_name, payer_email, store_order_reference, store_payment_request_id,
                               processor_payment_id, processor_approved_at, processor_installments, purchase_description
                        from actionfinance.pay_receipt_transaction
                        where transaction_id = 'py-real'
                        """);
        assertThat(stored.get("payer_name")).isEqualTo("Pagador Exemplo");
        assertThat(stored.get("payer_email")).isEqualTo("pagador.exemplo@exemplo.test");
        assertThat(stored.get("store_order_reference")).isEqualTo("PED-1042");
        assertThat(stored.get("store_payment_request_id")).isEqualTo("req-77");
        assertThat(stored.get("processor_payment_id")).isEqualTo("mp-1");
        assertThat(stored.get("processor_approved_at")).isEqualTo("2026-11-09T18:04:11Z");
        assertThat(stored.get("processor_installments")).isEqualTo(2);
        assertThat(stored.get("purchase_description")).isEqualTo("Fornada de sábado");
        Map<String, Object> unnamed =
                jdbc.queryForMap(
                        "select payer_name, payer_email from actionfinance.pay_receipt_transaction where transaction_id = 'py-tech'");
        assertThat(unnamed.get("payer_name")).isNull();
        assertThat(unnamed.get("payer_email")).isNull();
        JsonNode overview =
                mapper.readTree(
                        mockMvc.perform(
                                        get("/api/v1/pay-receipts")
                                                .header("Authorization", "Bearer " + OPERATOR)
                                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString()))
                                .andExpect(status().isOk())
                                .andReturn()
                                .getResponse()
                                .getContentAsString());
        JsonNode exposed = null;
        for (JsonNode item : overview.path("items")) {
            if ("py-real".equals(item.path("transactionId").asText())) {
                exposed = item;
            }
        }
        assertThat(exposed).isNotNull();
        assertThat(exposed.path("payerName").asText()).isEqualTo("Pagador Exemplo");
        assertThat(exposed.path("payerEmail").asText()).isEqualTo("pagador.exemplo@exemplo.test");
        assertThat(exposed.path("storeOrderReference").asText()).isEqualTo("PED-1042");
        assertThat(exposed.path("storePaymentRequestId").asText()).isEqualTo("req-77");
        assertThat(exposed.path("processorPaymentId").asText()).isEqualTo("mp-1");
        assertThat(exposed.path("processorApprovedAt").asText()).isEqualTo("2026-11-09T18:04:11Z");
        assertThat(exposed.path("processorInstallments").asInt()).isEqualTo(2);
        assertThat(exposed.path("purchaseDescription").asText()).isEqualTo("Fornada de sábado");
        String logs =
                appender.list.stream()
                        .map(ch.qos.logback.classic.spi.ILoggingEvent::getFormattedMessage)
                        .reduce("", String::concat);
        assertThat(logs).doesNotContain("Pagador Exemplo");
        assertThat(logs).doesNotContain("pagador.exemplo@exemplo.test");
        assertThat(logs).doesNotContain("amount.hub.local");
    }

    private static SpiderListResult page(String correlation, List<Map<String, Object>> items, String next) {
        return page(correlation, items, List.of(), next, "HOMOLOG");
    }

    private static SpiderListResult page(
            String correlation,
            List<Map<String, Object>> items,
            List<Map<String, Object>> reviews,
            String next,
            String environment) {
        return new SpiderListResult(
                true,
                "READY",
                "spd-1",
                "PRESENT_EXTERNAL_LIST",
                "SATELLITE_CONTRACT_V1_4_THEN_CAPABILITY_RESOLUTION",
                "LIST_PAYMENT_TRANSACTIONS",
                correlation,
                "afm-" + correlation,
                environment,
                items.size(),
                next,
                items,
                reviews,
                null,
                null);
    }

    private static Map<String, Object> item(
            String id, String original, String normalized, String amount, String updatedAt) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("transactionId", id);
        item.put("orderReference", id);
        item.put("originalStatus", original);
        item.put("normalizedStatus", normalized);
        item.put("amountMinor", amount);
        item.put("amountAbsent", amount == null);
        item.put("currency", amount == null ? null : "BRL");
        item.put("updatedAt", updatedAt);
        item.put("originRevision", updatedAt);
        item.put("testLabeled", true);
        item.put("reviewRequired", amount == null);
        return item;
    }

    private static Map<String, Object> review(
            String id,
            String original,
            String normalized,
            String charged,
            String paid,
            String classification,
            String updatedAt) {
        Map<String, Object> row = item(id, original, normalized, charged, updatedAt);
        row.put("classification", classification);
        row.put("classificationReason", "sem live_mode");
        row.put("paidAmountMinor", paid);
        row.put("paidAmountAbsent", paid == null);
        row.put("reviewRequired", true);
        return row;
    }

    private static Map<String, Object> commercialItem(
            String id,
            String original,
            String normalized,
            String charged,
            String paid,
            String classification,
            String updatedAt,
            String payer,
            String method) {
        Map<String, Object> row = item(id, original, normalized, charged, updatedAt);
        row.put("classification", classification);
        row.put("paidAmountMinor", paid);
        row.put("paidAmountAbsent", paid == null);
        row.put("payerKind", payer == null ? "ABSENT" : "EMAIL");
        row.put("payerLabel", payer);
        row.put("payerProvenance", payer == null ? null : "ACTIONHUB_PAY");
        row.put("paymentMethod", method);
        row.put("commercialApplication", "lojadepaes");
        row.put("commercialDescription", "Consulta avulsa");
        row.put("processorName", method == null ? null : "Mercado Pago");
        row.put("providerStatus", paid == null ? null : "approved");
        row.put("reviewRequired", charged == null);
        row.put("testLabeled", !"REAL".equals(classification));
        return row;
    }
}
