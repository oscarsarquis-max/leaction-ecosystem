package br.com.actionfinance;

import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.application.integration.PayReceiptSyncCycle;
import br.com.actionfinance.application.integration.PayReceiptSyncScheduling;
import br.com.actionfinance.application.integration.SpiderInteractionClient;
import br.com.actionfinance.application.integration.SpiderInteractionClient.SpiderListResult;
import br.com.actionfinance.support.PostgresFoundationContainer;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;
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

import javax.sql.DataSource;
import java.sql.Connection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("local-demo")
@Testcontainers
class PayReceiptSyncSchedulerIT {

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
        registry.add("actionfinance.demo-auth.viewer-a-token", () -> "viewer-a-demo-token-bbbbbbbbbbbbbbbbbbbb");
        registry.add("actionfinance.demo-auth.viewer-b-token", () -> "viewer-b-demo-token-cccccccccccccccccccc");
        registry.add("actionfinance.demo-auth.operator-multi-token", () -> "operator-multi-token-dddddddddddddddddd");
        registry.add("actionfinance.integration.homolog", () -> "true");
        registry.add("actionfinance.pay-sync.scheduler-enabled", () -> "false");
    }

    @Autowired
    PayReceiptSyncCycle cycle;

    @Autowired
    ObjectProvider<PayReceiptSyncScheduling> scheduling;

    @Autowired
    MockMvc mockMvc;

    @Autowired
    JdbcTemplate jdbc;

    @Autowired
    DataSource dataSource;

    @MockBean
    SpiderInteractionClient spider;

    @BeforeEach
    void clean() {
        jdbc.update(
                """
                update actionfinance.pay_receipt_sync_run
                set status = 'FAILED', finished_at = now(), updated_at = now(), last_error = 'ensaio encerrado'
                where company_id in (?, ?) and status = 'RUNNING'
                """,
                DemoPrincipalCatalog.COMPANY_A,
                DemoPrincipalCatalog.COMPANY_B);
        jdbc.update(
                """
                insert into actionfinance.pay_company_mapping (
                    id, tenant_id, company_id, pay_app_id, environment, authorized, created_at, updated_at)
                values (?, ?, ?, 'homolog-empresa-b', 'HOMOLOG', true, now(), now())
                on conflict (tenant_id, company_id) do update set authorized = true, environment = 'HOMOLOG'
                """,
                UUID.fromString("22222222-aaaa-4222-a222-222222222801"),
                DemoPrincipalCatalog.TENANT_B,
                DemoPrincipalCatalog.COMPANY_B);
        jdbc.update(
                "update actionfinance.pay_company_mapping set authorized = true where company_id = ?",
                DemoPrincipalCatalog.COMPANY_A);
    }

    @Test
    void schedulerStaysOffInLocalDemo() {
        assertThat(scheduling.getIfAvailable()).isNull();
    }

    @Test
    void cycleCallsTheServiceOncePerActiveCompanyAndRecordsAutomaticOrigin() {
        when(spider.list(any(), any(), any(), any(), any(), anyInt())).thenReturn(emptyPage("ciclo"));
        cycle.run();
        verify(spider, times(1)).list(any(), any(), eq(DemoPrincipalCatalog.COMPANY_A.toString()), any(), any(), anyInt());
        verify(spider, times(1)).list(any(), any(), eq(DemoPrincipalCatalog.COMPANY_B.toString()), any(), any(), anyInt());
        assertThat(triggerOf(DemoPrincipalCatalog.COMPANY_A)).isEqualTo("AUTOMATIC");
        assertThat(triggerOf(DemoPrincipalCatalog.COMPANY_B)).isEqualTo("AUTOMATIC");
    }

    @Test
    void cycleSkipsTheCompanyThatAlreadyHasARunningSync() {
        jdbc.update(
                """
                insert into actionfinance.pay_receipt_sync_run (
                    id, tenant_id, company_id, origin_system, environment, status,
                    root_correlation_id, page_count, imported_count, updated_count, review_count,
                    started_at, created_at, updated_at, trigger_kind)
                values (
                    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa57', ?, ?, 'ACTIONHUB_PAY', 'HOMOLOG',
                    'RUNNING', 'afr-manual', 0, 0, 0, 0, now(), now(), now(), 'MANUAL')
                """,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A);
        when(spider.list(any(), any(), any(), any(), any(), anyInt())).thenReturn(emptyPage("livre"));
        cycle.run();
        verify(spider, never()).list(any(), any(), eq(DemoPrincipalCatalog.COMPANY_A.toString()), any(), any(), anyInt());
        verify(spider, times(1)).list(any(), any(), eq(DemoPrincipalCatalog.COMPANY_B.toString()), any(), any(), anyInt());
        assertThat(statusOf(DemoPrincipalCatalog.COMPANY_A)).isEqualTo("RUNNING");
        assertThat(statusOf(DemoPrincipalCatalog.COMPANY_B)).isEqualTo("EMPTY");
    }

    @Test
    void failureOfOneCompanyDoesNotStopTheOthers() {
        when(spider.list(any(), any(), any(), any(), any(), anyInt()))
                .thenAnswer(
                        invocation -> {
                            String companyId = invocation.getArgument(2);
                            if (DemoPrincipalCatalog.COMPANY_A.toString().equals(companyId)) {
                                throw new IllegalStateException("falha isolada");
                            }
                            return emptyPage("segue");
                        });
        cycle.run();
        assertThat(statusOf(DemoPrincipalCatalog.COMPANY_A)).isEqualTo("FAILED");
        assertThat(statusOf(DemoPrincipalCatalog.COMPANY_B)).isEqualTo("EMPTY");
        assertThat(triggerOf(DemoPrincipalCatalog.COMPANY_B)).isEqualTo("AUTOMATIC");
    }

    @Test
    void repeatWithoutNewsDoesNotStoreAnotherReceipt() {
        when(spider.list(any(), any(), any(), any(), any(), anyInt()))
                .thenAnswer(
                        invocation -> {
                            String companyId = invocation.getArgument(2);
                            if (DemoPrincipalCatalog.COMPANY_A.toString().equals(companyId)) {
                                return pageOf(item("auto-estavel", "PAID", "CONFIRMED", "1500", "2026-11-09T15:00:00Z"));
                            }
                            return emptyPage("vazio");
                        });
        cycle.run();
        Integer afterFirst = countReceipts("auto-estavel");
        cycle.run();
        assertThat(afterFirst).isEqualTo(1);
        assertThat(countReceipts("auto-estavel")).isEqualTo(1);
        Integer imported =
                jdbc.queryForObject(
                        """
                        select imported_count from actionfinance.pay_receipt_sync_run
                        where company_id = ? and trigger_kind = 'AUTOMATIC'
                        order by started_at desc
                        limit 1
                        """,
                        Integer.class,
                        DemoPrincipalCatalog.COMPANY_A);
        Integer updated =
                jdbc.queryForObject(
                        """
                        select updated_count from actionfinance.pay_receipt_sync_run
                        where company_id = ? and trigger_kind = 'AUTOMATIC'
                        order by started_at desc
                        limit 1
                        """,
                        Integer.class,
                        DemoPrincipalCatalog.COMPANY_A);
        assertThat(imported).isZero();
        assertThat(updated).isZero();
    }

    @Test
    void manualSyncRecordsManualOrigin() throws Exception {
        when(spider.list(any(), any(), any(), any(), any(), anyInt())).thenReturn(emptyPage("manual"));
        mockMvc.perform(
                        post("/api/v1/pay-receipts/sync")
                                .header("Authorization", "Bearer " + OPERATOR)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.run.trigger").value("MANUAL"));
    }

    @Test
    void secondCycleWaitsWhileAnotherConnectionHoldsTheLock() throws Exception {
        when(spider.list(any(), any(), any(), any(), any(), anyInt())).thenReturn(emptyPage("lock"));
        try (Connection connection = dataSource.getConnection();
                var statement = connection.prepareStatement("select pg_try_advisory_lock(?)")) {
            statement.setLong(1, PayReceiptSyncCycle.LOCK_KEY);
            try (var result = statement.executeQuery()) {
                assertThat(result.next()).isTrue();
                assertThat(result.getBoolean(1)).isTrue();
            }
            cycle.run();
            verify(spider, never()).list(any(), any(), any(), any(), any(), anyInt());
            try (var unlock = connection.prepareStatement("select pg_advisory_unlock(?)")) {
                unlock.setLong(1, PayReceiptSyncCycle.LOCK_KEY);
                unlock.execute();
            }
        }
        cycle.run();
        verify(spider, times(1)).list(any(), any(), eq(DemoPrincipalCatalog.COMPANY_A.toString()), any(), any(), anyInt());
    }

    private String triggerOf(UUID companyId) {
        return jdbc.queryForObject(
                """
                select trigger_kind from actionfinance.pay_receipt_sync_run
                where company_id = ?
                order by started_at desc
                limit 1
                """,
                String.class,
                companyId);
    }

    private String statusOf(UUID companyId) {
        return jdbc.queryForObject(
                """
                select status from actionfinance.pay_receipt_sync_run
                where company_id = ?
                order by started_at desc
                limit 1
                """,
                String.class,
                companyId);
    }

    private Integer countReceipts(String transactionId) {
        Integer value =
                jdbc.queryForObject(
                        "select count(*) from actionfinance.pay_receipt_transaction where transaction_id = ?",
                        Integer.class,
                        transactionId);
        return value == null ? 0 : value;
    }

    private static SpiderListResult emptyPage(String correlation) {
        return pageOf(correlation, List.of());
    }

    private static SpiderListResult pageOf(Map<String, Object> item) {
        return pageOf("auto", List.of(item));
    }

    private static SpiderListResult pageOf(String correlation, List<Map<String, Object>> items) {
        return new SpiderListResult(
                true,
                "READY",
                "spd-auto",
                "PRESENT_EXTERNAL_LIST",
                "SATELLITE_CONTRACT_V1_4_THEN_CAPABILITY_RESOLUTION",
                "LIST_PAYMENT_TRANSACTIONS",
                correlation,
                "afm-" + correlation,
                "HOMOLOG",
                items.size(),
                null,
                items,
                List.of(),
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
        item.put("amountAbsent", false);
        item.put("currency", "BRL");
        item.put("updatedAt", updatedAt);
        item.put("originRevision", updatedAt);
        item.put("classification", "TEST");
        item.put("testLabeled", true);
        item.put("reviewRequired", false);
        return item;
    }
}
