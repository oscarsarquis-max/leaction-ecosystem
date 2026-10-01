package br.com.actionfinance;

import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.application.finance.LocalDemoSeed;
import br.com.actionfinance.application.integration.LookupConcurrencyGate;
import br.com.actionfinance.application.integration.SpiderInteractionClient;
import br.com.actionfinance.support.PostgresFoundationContainer;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
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

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("local-demo")
@Testcontainers
class ExternalLookupReliabilityIT {

    private static final String OPERATOR = "operator-demo-token-aaaaaaaaaaaaaaaaaaaa";
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
        registry.add("actionfinance.demo-auth.viewer-a-token", () -> "viewer-a-demo-token-bbbbbbbbbbbbbbbbbbbb");
        registry.add("actionfinance.demo-auth.viewer-b-token", () -> "viewer-b-demo-token-cccccccccccccccccccc");
        registry.add("actionfinance.demo-auth.operator-multi-token", () -> MULTI);
        registry.add("actionfinance.clock.zone", () -> "America/Sao_Paulo");
        registry.add("actionfinance.clock.fixed-instant", () -> "2026-09-15T15:00:00Z");
        registry.add("actionfinance.integration.homolog", () -> "true");
        registry.add("actionfinance.integration.lookup-stale-after", () -> "PT1S");
    }

    @Autowired
    MockMvc mockMvc;

    @Autowired
    ObjectMapper mapper;

    @Autowired
    JdbcTemplate jdbc;

    @Autowired
    LookupConcurrencyGate gate;

    @MockBean
    SpiderInteractionClient spider;

    @BeforeEach
    void resetLookupRows() {
        gate.reset();
        jdbc.update(
                "update actionfinance.pay_company_mapping set authorized = true where company_id = ?",
                DemoPrincipalCatalog.COMPANY_A);
    }

    @Test
    void concurrentFirstCreateKeepsSingleOperation() throws Exception {
        when(spider.lookup(any(), any(), any(), any(), any()))
                .thenAnswer(invocation -> ready("pay-conc-0001", "12550", "CONFIRMED", "2026-09-30T12:00:00Z", invocation.getArgument(0)));
        var pool = Executors.newFixedThreadPool(2);
        CountDownLatch start = new CountDownLatch(1);
        Future<MvcResult> first =
                pool.submit(
                        () -> {
                            start.await(5, TimeUnit.SECONDS);
                            return consult(LocalDemoSeed.TITLE_REC_SALE, "pay-conc-0001", OPERATOR);
                        });
        Future<MvcResult> second =
                pool.submit(
                        () -> {
                            start.await(5, TimeUnit.SECONDS);
                            return consult(LocalDemoSeed.TITLE_REC_SALE, "pay-conc-0001", OPERATOR);
                        });
        start.countDown();
        MvcResult a = first.get(15, TimeUnit.SECONDS);
        MvcResult b = second.get(15, TimeUnit.SECONDS);
        pool.shutdownNow();
        assertThat(a.getResponse().getStatus()).isEqualTo(200);
        assertThat(b.getResponse().getStatus()).isEqualTo(200);
        JsonNode left = mapper.readTree(a.getResponse().getContentAsString());
        JsonNode right = mapper.readTree(b.getResponse().getContentAsString());
        assertThat(left.get("id").asText()).isEqualTo(right.get("id").asText());
        Integer operations =
                jdbc.queryForObject(
                        "select count(*) from actionfinance.external_operation where external_reference = 'pay-conc-0001'",
                        Integer.class);
        assertThat(operations).isEqualTo(1);
        Integer attempts =
                jdbc.queryForObject(
                        """
                        select count(*) from actionfinance.lookup_attempt a
                        join actionfinance.external_operation o on o.id = a.operation_id
                        where o.external_reference = 'pay-conc-0001'
                        """,
                        Integer.class);
        assertThat(attempts).isEqualTo(2);
        Integer distinct =
                jdbc.queryForObject(
                        """
                        select count(distinct a.id) from actionfinance.lookup_attempt a
                        join actionfinance.external_operation o on o.id = a.operation_id
                        where o.external_reference = 'pay-conc-0001'
                        """,
                        Integer.class);
        assertThat(distinct).isEqualTo(2);
        Integer unpairedStarts =
                jdbc.queryForObject(
                        """
                        select count(*) from actionfinance.lookup_attempt a
                        join actionfinance.external_operation o on o.id = a.operation_id
                        where o.external_reference = 'pay-conc-0001' and a.completed_at is null
                        """,
                        Integer.class);
        assertThat(unpairedStarts).isZero();
    }

    @Test
    void sameReferenceOnAnotherTitleIsConflict() throws Exception {
        when(spider.lookup(any(), any(), any(), any(), any()))
                .thenAnswer(invocation -> ready("pay-bind-0001", "12550", "CONFIRMED", "2026-09-30T12:00:00Z", invocation.getArgument(0)));
        consult(LocalDemoSeed.TITLE_REC_SALE, "pay-bind-0001", OPERATOR);
        mockMvc.perform(
                        post("/api/v1/receivables/{id}/pay-lookup", LocalDemoSeed.TITLE_REC_SUB)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"externalReference\":\"pay-bind-0001\"}"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("BINDING_CONFLICT"));
    }

    @Test
    void distinctCompaniesKeepSeparateOperations() throws Exception {
        jdbc.update(
                """
                insert into actionfinance.pay_company_mapping (
                    id, tenant_id, company_id, pay_app_id, environment, authorized, created_at, updated_at)
                values (?,?,?,?, 'HOMOLOG', true, now(), now())
                on conflict (tenant_id, company_id) do update set authorized = true
                """,
                UUID.fromString("33333333-aaaa-4333-a333-333333333801"),
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_C,
                "homolog-clinica");
        when(spider.lookup(any(), any(), any(), any(), any()))
                .thenAnswer(
                        invocation ->
                                ready(
                                        invocation.getArgument(4),
                                        "12550",
                                        "CONFIRMED",
                                        "2026-09-30T12:00:00Z",
                                        invocation.getArgument(0)));
        MvcResult padaria = consult(LocalDemoSeed.TITLE_REC_SALE, "pay-shared-ref", OPERATOR);
        MvcResult clinic =
                mockMvc.perform(
                                post("/api/v1/receivables/{id}/pay-lookup", LocalDemoSeed.TITLE_CLINIC_REC)
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_C.toString())
                                        .header("Authorization", "Bearer " + MULTI)
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content("{\"externalReference\":\"pay-shared-ref\"}"))
                        .andExpect(status().isOk())
                        .andReturn();
        assertThat(mapper.readTree(padaria.getResponse().getContentAsString()).get("id").asText())
                .isNotEqualTo(mapper.readTree(clinic.getResponse().getContentAsString()).get("id").asText());
    }

    @Test
    void revokedMappingHidesReplayAndBlocksNewConsult() throws Exception {
        when(spider.lookup(any(), any(), any(), any(), any()))
                .thenAnswer(invocation -> ready("pay-rev-0001", "12550", "CONFIRMED", "2026-09-30T12:00:00Z", invocation.getArgument(0)));
        consult(LocalDemoSeed.TITLE_REC_SALE, "pay-rev-0001", OPERATOR);
        jdbc.update(
                "update actionfinance.pay_company_mapping set authorized = false where company_id = ?",
                DemoPrincipalCatalog.COMPANY_A);
        mockMvc.perform(
                        get("/api/v1/receivables/{id}/pay-lookup", LocalDemoSeed.TITLE_REC_SALE)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isNotFound());
        mockMvc.perform(
                        post("/api/v1/receivables/{id}/pay-lookup", LocalDemoSeed.TITLE_REC_SALE)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"externalReference\":\"pay-rev-0001\"}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void lateProviderObservationDoesNotEraseNewerConfirmed() throws Exception {
        AtomicInteger calls = new AtomicInteger();
        when(spider.lookup(any(), any(), any(), any(), any()))
                .thenAnswer(
                        invocation -> {
                            String correlation = invocation.getArgument(0);
                            if (calls.incrementAndGet() == 1) {
                                return ready("pay-late-0001", "12550", "CONFIRMED", "2026-09-30T12:00:00Z", correlation);
                            }
                            return ready("pay-late-0001", "12550", "REFUNDED", "2026-09-30T11:00:00Z", correlation);
                        });
        consult(LocalDemoSeed.TITLE_REC_SALE, "pay-late-0001", OPERATOR);
        MvcResult late = consult(LocalDemoSeed.TITLE_REC_SALE, "pay-late-0001", OPERATOR);
        JsonNode body = mapper.readTree(late.getResponse().getContentAsString());
        assertThat(body.get("externalStatus").asText()).isEqualTo("CONFIRMED");
        assertThat(body.get("lastAttemptOutcome").asText()).isEqualTo("DELIVERED");
    }

    @Test
    void timeoutAfterConfirmKeepsObservation() throws Exception {
        AtomicInteger calls = new AtomicInteger();
        when(spider.lookup(any(), any(), any(), any(), any()))
                .thenAnswer(
                        invocation -> {
                            if (calls.incrementAndGet() == 1) {
                                return ready(
                                        "pay-to-0001",
                                        "12550",
                                        "CONFIRMED",
                                        "2026-09-30T12:00:00Z",
                                        invocation.getArgument(0));
                            }
                            return SpiderInteractionClient.SpiderLookupResult.unavailable("afc-to", "timeout");
                        });
        consult(LocalDemoSeed.TITLE_REC_SALE, "pay-to-0001", OPERATOR);
        MvcResult timed = consult(LocalDemoSeed.TITLE_REC_SALE, "pay-to-0001", OPERATOR);
        JsonNode body = mapper.readTree(timed.getResponse().getContentAsString());
        assertThat(body.get("externalStatus").asText()).isEqualTo("CONFIRMED");
        assertThat(body.get("amountMinor").asText()).isEqualTo("12550");
        assertThat(body.get("lastAttemptOutcome").asText()).isEqualTo("UNAVAILABLE");
    }

    @Test
    void staleResponseIsNotMarkedApplied() throws Exception {
        AtomicInteger calls = new AtomicInteger();
        when(spider.lookup(any(), any(), any(), any(), any()))
                .thenAnswer(
                        invocation -> {
                            String correlation = invocation.getArgument(0);
                            if (calls.incrementAndGet() == 1) {
                                return ready("pay-stale-0001", "12550", "CONFIRMED", "2026-09-30T12:00:00Z", correlation);
                            }
                            return ready("pay-stale-0001", "12550", "REFUNDED", "2026-09-30T11:00:00Z", correlation);
                        });
        consult(LocalDemoSeed.TITLE_REC_SALE, "pay-stale-0001", OPERATOR);
        consult(LocalDemoSeed.TITLE_REC_SALE, "pay-stale-0001", OPERATOR);
        Integer appliedStale =
                jdbc.queryForObject(
                        """
                        select count(*) from actionfinance.lookup_attempt a
                        join actionfinance.external_operation o on o.id = a.operation_id
                        where o.external_reference = 'pay-stale-0001'
                          and a.discarded_reason = 'STALE'
                          and a.observation_applied = true
                        """,
                        Integer.class);
        assertThat(appliedStale).isZero();
        Integer discarded =
                jdbc.queryForObject(
                        """
                        select count(*) from actionfinance.lookup_attempt a
                        join actionfinance.external_operation o on o.id = a.operation_id
                        where o.external_reference = 'pay-stale-0001' and a.discarded_reason = 'STALE'
                        """,
                        Integer.class);
        assertThat(discarded).isEqualTo(1);
    }

    @Test
    void persistedStartWithoutResponseIsRecoveredWithoutLosingObservation() throws Exception {
        when(spider.lookup(any(), any(), any(), any(), any()))
                .thenAnswer(
                        invocation ->
                                ready("pay-recov-0001", "12550", "CONFIRMED", "2026-09-30T12:00:00Z", invocation.getArgument(0)));
        MvcResult first = consult(LocalDemoSeed.TITLE_REC_SALE, "pay-recov-0001", OPERATOR);
        JsonNode created = mapper.readTree(first.getResponse().getContentAsString());
        UUID operationId = UUID.fromString(created.get("id").asText());
        UUID staleAttempt = UUID.fromString("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbb0009");
        jdbc.update(
                """
                insert into actionfinance.lookup_attempt (
                    id, tenant_id, company_id, operation_id, correlation_id, outcome, created_at,
                    started_at, completed_at, received_outcome, observation_applied, discarded_reason,
                    attempt_correlation_id)
                values (?,?,?,?,?, 'STARTED', now() - interval '2 minutes', now() - interval '2 minutes',
                        null, null, false, null, ?)
                """,
                staleAttempt,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                operationId,
                "afa-" + staleAttempt,
                "afa-" + staleAttempt);
        jdbc.update(
                """
                update actionfinance.external_operation
                set last_attempt_outcome = 'STARTED', last_attempt_at = now() - interval '2 minutes',
                    last_attempt_id = ?
                where id = ?
                """,
                staleAttempt,
                operationId);
        mockMvc.perform(
                        get("/api/v1/receivables/{id}/pay-lookup", LocalDemoSeed.TITLE_REC_SALE)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.externalStatus").value("CONFIRMED"))
                .andExpect(jsonPath("$.lastAttemptOutcome").value("UNAVAILABLE"));
        String discarded =
                jdbc.queryForObject(
                        "select discarded_reason from actionfinance.lookup_attempt where id = ?",
                        String.class,
                        staleAttempt);
        assertThat(discarded).isEqualTo("RECOVERED");
        String status =
                jdbc.queryForObject(
                        "select external_status from actionfinance.external_operation where id = ?",
                        String.class,
                        operationId);
        assertThat(status).isEqualTo("CONFIRMED");
    }

    @Test
    void recoveringExpiredAttemptDoesNotDiscardNewerStartedAttempt() throws Exception {
        when(spider.lookup(any(), any(), any(), any(), any()))
                .thenAnswer(
                        invocation ->
                                ready(
                                        "pay-race-ab-0001",
                                        "12550",
                                        "CONFIRMED",
                                        "2026-09-30T12:00:00Z",
                                        invocation.getArgument(0)));
        MvcResult first = consult(LocalDemoSeed.TITLE_REC_SALE, "pay-race-ab-0001", OPERATOR);
        UUID operationId = UUID.fromString(mapper.readTree(first.getResponse().getContentAsString()).get("id").asText());
        UUID expiredA = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa00a1");
        jdbc.update(
                """
                insert into actionfinance.lookup_attempt (
                    id, tenant_id, company_id, operation_id, correlation_id, outcome, created_at,
                    started_at, completed_at, received_outcome, observation_applied, discarded_reason,
                    attempt_correlation_id)
                values (?,?,?,?,?, 'STARTED', now() - interval '2 minutes', now() - interval '2 minutes',
                        null, null, false, null, ?)
                """,
                expiredA,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                operationId,
                "afa-" + expiredA,
                "afa-" + expiredA);
        jdbc.update(
                """
                update actionfinance.external_operation
                set last_attempt_outcome = 'STARTED', last_attempt_at = now() - interval '2 minutes',
                    last_attempt_id = ?, external_status = 'CONFIRMED'
                where id = ?
                """,
                expiredA,
                operationId);
        CountDownLatch readA = new CountDownLatch(1);
        CountDownLatch startedB = new CountDownLatch(1);
        CountDownLatch recoveredA = new CountDownLatch(1);
        gate.setAfterReadForRecover(
                () -> {
                    readA.countDown();
                    await(startedB);
                });
        gate.setAfterBeginAttempt(
                () -> {
                    startedB.countDown();
                    await(recoveredA);
                });
        gate.setAfterRecover(recoveredA::countDown);
        when(spider.lookup(any(), any(), any(), any(), any()))
                .thenAnswer(
                        invocation ->
                                ready(
                                        "pay-race-ab-0001",
                                        "12550",
                                        "REFUNDED",
                                        "2026-09-30T13:00:00Z",
                                        invocation.getArgument(0)));
        var pool = Executors.newFixedThreadPool(2);
        Future<MvcResult> get =
                pool.submit(
                        () ->
                                mockMvc.perform(
                                                get("/api/v1/receivables/{id}/pay-lookup", LocalDemoSeed.TITLE_REC_SALE)
                                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                                        .header("Authorization", "Bearer " + OPERATOR))
                                        .andReturn());
        assertThat(readA.await(5, TimeUnit.SECONDS)).isTrue();
        Future<MvcResult> post =
                pool.submit(
                        () -> {
                            gate.suppressRecoverOnThisThread(true);
                            try {
                                return consult(LocalDemoSeed.TITLE_REC_SALE, "pay-race-ab-0001", OPERATOR);
                            } finally {
                                gate.suppressRecoverOnThisThread(false);
                            }
                        });
        MvcResult recovered = get.get(15, TimeUnit.SECONDS);
        assertThat(recovered.getResponse().getStatus()).isEqualTo(200);
        assertThat(
                        jdbc.queryForObject(
                                "select discarded_reason from actionfinance.lookup_attempt where id = ?",
                                String.class,
                                expiredA))
                .isEqualTo("RECOVERED");
        assertThat(
                        jdbc.queryForObject(
                                "select last_attempt_id from actionfinance.external_operation where id = ?",
                                UUID.class,
                                operationId))
                .isNotEqualTo(expiredA);
        assertThat(
                        jdbc.queryForObject(
                                "select last_attempt_outcome from actionfinance.external_operation where id = ?",
                                String.class,
                                operationId))
                .isEqualTo("STARTED");
        MvcResult newer = post.get(15, TimeUnit.SECONDS);
        pool.shutdownNow();
        assertThat(newer.getResponse().getStatus()).isEqualTo(200);
        JsonNode body = mapper.readTree(newer.getResponse().getContentAsString());
        assertThat(body.get("externalStatus").asText()).isEqualTo("REFUNDED");
        assertThat(body.get("lastAttemptOutcome").asText()).isEqualTo("DELIVERED");
        assertThat(body.get("lastAttemptId").asText()).isNotEqualTo(expiredA.toString());
        assertThat(
                        jdbc.queryForObject(
                                "select discarded_reason from actionfinance.lookup_attempt where id = ?",
                                String.class,
                                expiredA))
                .isEqualTo("RECOVERED");
        assertThat(
                        jdbc.queryForObject(
                                "select observation_applied from actionfinance.lookup_attempt where id = ?",
                                Boolean.class,
                                expiredA))
                .isFalse();
        UUID attemptB = UUID.fromString(body.get("lastAttemptId").asText());
        assertThat(
                        jdbc.queryForObject(
                                "select outcome from actionfinance.lookup_attempt where id = ?",
                                String.class,
                                attemptB))
                .isEqualTo("DELIVERED");
        assertThat(
                        jdbc.queryForObject(
                                "select discarded_reason from actionfinance.lookup_attempt where id = ?",
                                String.class,
                                attemptB))
                .isNull();
    }

    @Test
    void recoverAndCompleteSameAttemptStayConsistent() throws Exception {
        when(spider.lookup(any(), any(), any(), any(), any()))
                .thenAnswer(
                        invocation ->
                                ready(
                                        "pay-race-same-0001",
                                        "12550",
                                        "CONFIRMED",
                                        "2026-09-30T12:00:00Z",
                                        invocation.getArgument(0)));
        MvcResult first = consult(LocalDemoSeed.TITLE_REC_SALE, "pay-race-same-0001", OPERATOR);
        UUID operationId = UUID.fromString(mapper.readTree(first.getResponse().getContentAsString()).get("id").asText());
        CountDownLatch aged = new CountDownLatch(1);
        CountDownLatch allowLookup = new CountDownLatch(1);
        CountDownLatch arrivedRecover = new CountDownLatch(1);
        CountDownLatch arrivedComplete = new CountDownLatch(1);
        CountDownLatch go = new CountDownLatch(1);
        when(spider.lookup(any(), any(), any(), any(), any()))
                .thenAnswer(
                        invocation -> {
                            await(allowLookup);
                            return ready(
                                    "pay-race-same-0001",
                                    "12550",
                                    "REFUNDED",
                                    "2026-09-30T13:00:00Z",
                                    invocation.getArgument(0));
                        });
        gate.setAfterBeginAttempt(
                () -> {
                    jdbc.update(
                            """
                            update actionfinance.lookup_attempt
                            set started_at = now() - interval '2 minutes'
                            where operation_id = ? and outcome = 'STARTED' and completed_at is null
                            """,
                            operationId);
                    jdbc.update(
                            """
                            update actionfinance.external_operation
                            set last_attempt_at = now() - interval '2 minutes'
                            where id = ?
                            """,
                            operationId);
                    aged.countDown();
                });
        gate.setBeforeRecover(
                () -> {
                    arrivedRecover.countDown();
                    await(go);
                });
        gate.setBeforeComplete(
                () -> {
                    arrivedComplete.countDown();
                    await(go);
                });
        var pool = Executors.newFixedThreadPool(3);
        Future<MvcResult> consult =
                pool.submit(() -> consult(LocalDemoSeed.TITLE_REC_SALE, "pay-race-same-0001", OPERATOR));
        assertThat(aged.await(5, TimeUnit.SECONDS)).isTrue();
        Future<MvcResult> get =
                pool.submit(
                        () ->
                                mockMvc.perform(
                                                get("/api/v1/receivables/{id}/pay-lookup", LocalDemoSeed.TITLE_REC_SALE)
                                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                                        .header("Authorization", "Bearer " + OPERATOR))
                                        .andReturn());
        allowLookup.countDown();
        assertThat(arrivedRecover.await(5, TimeUnit.SECONDS)).isTrue();
        assertThat(arrivedComplete.await(5, TimeUnit.SECONDS)).isTrue();
        go.countDown();
        assertThat(consult.get(15, TimeUnit.SECONDS).getResponse().getStatus()).isEqualTo(200);
        assertThat(get.get(15, TimeUnit.SECONDS).getResponse().getStatus()).isEqualTo(200);
        pool.shutdownNow();
        UUID raced =
                jdbc.queryForObject(
                        """
                        select id from actionfinance.lookup_attempt
                        where operation_id = ? and started_at <= now() - interval '1 minute'
                        order by started_at desc
                        limit 1
                        """,
                        UUID.class,
                        operationId);
        String outcome =
                jdbc.queryForObject(
                        "select outcome from actionfinance.lookup_attempt where id = ?", String.class, raced);
        String discarded =
                jdbc.queryForObject(
                        "select discarded_reason from actionfinance.lookup_attempt where id = ?", String.class, raced);
        Boolean applied =
                jdbc.queryForObject(
                        "select observation_applied from actionfinance.lookup_attempt where id = ?",
                        Boolean.class,
                        raced);
        String status =
                jdbc.queryForObject(
                        "select external_status from actionfinance.external_operation where id = ?",
                        String.class,
                        operationId);
        assertThat(jdbc.queryForObject(
                        "select completed_at is not null from actionfinance.lookup_attempt where id = ?",
                        Boolean.class,
                        raced))
                .isTrue();
        if ("RECOVERED".equals(discarded)) {
            assertThat(applied).isFalse();
            assertThat(status).isEqualTo("CONFIRMED");
            assertThat(outcome).isEqualTo("UNAVAILABLE");
        } else {
            assertThat(discarded).isNull();
            assertThat(outcome).isEqualTo("DELIVERED");
            if (Boolean.TRUE.equals(applied)) {
                assertThat(status).isEqualTo("REFUNDED");
            } else {
                assertThat(status).isEqualTo("CONFIRMED");
            }
        }
    }

    private static void await(CountDownLatch latch) {
        try {
            if (!latch.await(5, TimeUnit.SECONDS)) {
                throw new IllegalStateException("barrier");
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(e);
        }
    }

    private MvcResult consult(UUID titleId, String reference, String token) throws Exception {
        return mockMvc.perform(
                        post("/api/v1/receivables/{id}/pay-lookup", titleId)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + token)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"externalReference\":\"" + reference + "\"}"))
                .andExpect(status().isOk())
                .andReturn();
    }

    private static SpiderInteractionClient.SpiderLookupResult ready(
            String reference, String amount, String status, String observedAt, String correlationId) {
        return new SpiderInteractionClient.SpiderLookupResult(
                true,
                "READY",
                "spd-" + reference,
                "PRESENT_EXTERNAL_LOOKUP",
                "SATELLITE_CONTRACT_V1_3_THEN_CAPABILITY_RESOLUTION",
                "LOOKUP_ACTIONHUB_PAYMENT",
                correlationId,
                Map.of(
                        "externalStatus",
                        status,
                        "amountMinor",
                        amount,
                        "currency",
                        "BRL",
                        "providerReference",
                        reference,
                        "origin",
                        "SIMULATOR",
                        "providerObservedAt",
                        observedAt),
                null,
                null);
    }
}
