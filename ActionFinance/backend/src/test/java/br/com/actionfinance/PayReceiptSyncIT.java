package br.com.actionfinance;

import br.com.actionfinance.application.DemoPrincipalCatalog;
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

    private static SpiderListResult page(String correlation, List<Map<String, Object>> items, String next) {
        return new SpiderListResult(
                true,
                "READY",
                "spd-1",
                "PRESENT_EXTERNAL_LIST",
                "SATELLITE_CONTRACT_V1_4_THEN_CAPABILITY_RESOLUTION",
                "LIST_PAYMENT_TRANSACTIONS",
                correlation,
                "afm-" + correlation,
                "HOMOLOG",
                items.size(),
                next,
                items,
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
}
