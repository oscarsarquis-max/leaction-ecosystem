package br.com.banco.spider.operational.monitor;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.infrastructure.persistence.jdbc.JdbcMonitorProjectionStoreAdapter;
import br.com.banco.spider.infrastructure.persistence.jdbc.MonitorSchemaMigrator;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventType;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextBlock;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextSnapshot;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Objective;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Provenance;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

class MonitorProjectionPostgres16IT {

  private static final String COMPANY = "9c2e0a10-4f11-4b8a-9c2e-0a104f11000c";
  private static final String RUN_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
  private static final String RUN_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
  private static final String CONTAINER = "spider-monitor-pg16-it";
  private static final int PORT = 55432;

  @BeforeAll
  static void startPostgres() throws Exception {
    exec("docker", "rm", "-f", CONTAINER);
    int started =
        exec(
            "docker",
            "run",
            "-d",
            "--name",
            CONTAINER,
            "-e",
            "POSTGRES_USER=spider",
            "-e",
            "POSTGRES_PASSWORD=spider",
            "-e",
            "POSTGRES_DB=spider_monitor",
            "-p",
            PORT + ":5432",
            "postgres:16.6");
    assertEquals(0, started, "PostgreSQL 16 container must start for this proof");
    waitUntilReady();
  }

  @AfterAll
  static void stopPostgres() throws Exception {
    exec("docker", "rm", "-f", CONTAINER);
  }

  @Test
  void emptyDatabaseMigratesAndSurvivesRestart() {
    JdbcTemplate first = jdbc();
    new MonitorSchemaMigrator(first).migrate();
    assertEquals(3, historyCount(first));
    MonitorProjectionService service = new MonitorProjectionService(new JdbcMonitorProjectionStoreAdapter(first));
    service.touchInteraction(
        listRequest("list-" + RUN_A + "-1", "afp-" + RUN_A + "-1", "a1"),
        OperationalEventType.SATELLITE_RESPONSE_RETURNED,
        OperationalEventOutcome.SUCCESS,
        "READY");
    service.touchInteraction(
        listRequest("list-" + RUN_A + "-2", "afp-" + RUN_A + "-2", "a2"),
        OperationalEventType.SATELLITE_RESPONSE_RETURNED,
        OperationalEventOutcome.SUCCESS,
        "READY");
    service.recordDiscoveredPayments(
        listRequest("list-" + RUN_A + "-1", "afp-" + RUN_A + "-1", "a1"), listResult("pay-77", "PENDING"));
    service.touchInteraction(
        listRequest("list-" + RUN_B + "-1", "afp-" + RUN_B + "-1", "b1"),
        OperationalEventType.SATELLITE_RESPONSE_RETURNED,
        OperationalEventOutcome.SUCCESS,
        "READY");
    service.recordDiscoveredPayments(
        listRequest("list-" + RUN_B + "-1", "afp-" + RUN_B + "-1", "b1"), listResult("pay-77", "PAID"));
    service.touchInteraction(
        lookupRequest("afm-direct-1", "ext-9"),
        OperationalEventType.SATELLITE_RESPONSE_RETURNED,
        OperationalEventOutcome.SUCCESS,
        "READY");

    String syncA = MonitorProjectionIds.sync(COMPANY, "HOMOLOG", RUN_A);
    String syncB = MonitorProjectionIds.sync(COMPANY, "HOMOLOG", RUN_B);
    String payment = MonitorProjectionIds.payment(COMPANY, "pay-77");
    String interaction = MonitorProjectionIds.interaction(lookupRequest("afm-direct-1", "ext-9"));
    assertNotEquals(syncA, syncB);

    JdbcTemplate restarted = jdbc();
    new MonitorSchemaMigrator(restarted).migrate();
    assertEquals(3, historyCount(restarted));
    JdbcMonitorProjectionStoreAdapter store = new JdbcMonitorProjectionStoreAdapter(restarted);
    assertEquals("COMPLETED", store.findById(syncA).orElseThrow().technicalState());
    assertEquals(2, store.findById(syncA).orElseThrow().pagesConsulted());
    assertTrue(store.findById(syncB).isPresent());
    assertEquals("PAID", store.findById(payment).orElseThrow().financialState());
    assertEquals("int:actionfinance:afm-direct-1", store.findById(interaction).orElseThrow().recordId());
    assertTrue(store.isDurable());
  }

  @Test
  void checksumMismatchAndInterruptedMigrationFailSafe() {
    JdbcTemplate jdbc = jdbc("spider_monitor_fail");
    new MonitorSchemaMigrator(jdbc).migrate();
    jdbc.update("update tb_monitor_schema_history set checksum = 'deadbeef' where version like 'V20261013%'");
    assertThrows(IllegalStateException.class, () -> new MonitorSchemaMigrator(jdbc).migrate());
    jdbc.update(
        "update tb_monitor_schema_history set checksum = ? where version like 'V20261013%'",
        MonitorSchemaMigrator.sha256(read("V20261013__tb_monitor_projection.sql")));
    jdbc.update("update tb_monitor_schema_history set status = 'STARTED' where version like 'V20261015%'");
    IllegalStateException interrupted =
        assertThrows(IllegalStateException.class, () -> new MonitorSchemaMigrator(jdbc).migrate());
    assertTrue(interrupted.getMessage().contains("interrompida"));
  }

  @Test
  void newMigrationAppliesOnPopulatedDatabase() {
    JdbcTemplate jdbc = jdbc("spider_monitor_populated");
    jdbc.execute(
        """
        create table if not exists tb_monitor_schema_history (
          version varchar(120) primary key,
          checksum varchar(64) not null,
          applied_at timestamp not null,
          status varchar(20) not null default 'SUCCESS'
        )
        """);
    String sql13 = read("V20261013__tb_monitor_projection.sql");
    for (String statement : sql13.split(";")) {
      if (!statement.isBlank()) {
        jdbc.execute(statement);
      }
    }
    jdbc.update(
        "insert into tb_monitor_schema_history(version, checksum, applied_at, status) values (?,?,now(),'SUCCESS')",
        "V20261013__tb_monitor_projection.sql",
        MonitorSchemaMigrator.sha256(sql13));
    String sql14 = read("V20261014__monitor_projection_links.sql");
    for (String statement : sql14.split(";")) {
      if (!statement.isBlank()) {
        jdbc.execute(statement);
      }
    }
    jdbc.update(
        "insert into tb_monitor_schema_history(version, checksum, applied_at, status) values (?,?,now(),'SUCCESS')",
        "V20261014__monitor_projection_links.sql",
        MonitorSchemaMigrator.sha256(sql14));
    jdbc.update(
        "insert into tb_monitor_projection(record_id, kind, origin, company_id, technical_state, created_at, updated_at, projection_version, retention_until) values (?,?,?,?,?,now(),now(),1, now() + interval '90 day')",
        "pay:" + COMPANY + ":keep-me",
        MonitorProjectionRecord.KIND_PAYMENT,
        MonitorProjectionRecord.ORIGIN_ACTIONHUB_PAY,
        COMPANY,
        "COMPLETED");
    new MonitorSchemaMigrator(jdbc).migrate();
    assertEquals(3, historyCount(jdbc));
    assertEquals(1, jdbc.queryForObject("select count(*) from tb_monitor_projection", Integer.class));
    assertEquals(
        1,
        jdbc.queryForObject(
            "select count(*) from pg_indexes where indexname = 'idx_monitor_projection_correlation'", Integer.class));
  }

  @Test
  void concurrentUpsertKeepsSinglePaymentAndAdvancedState() throws Exception {
    JdbcTemplate jdbc = jdbc("spider_monitor_concurrency");
    new MonitorSchemaMigrator(jdbc).migrate();
    JdbcMonitorProjectionStoreAdapter store = new JdbcMonitorProjectionStoreAdapter(jdbc);
    MonitorProjectionService service = new MonitorProjectionService(store);
    CountDownLatch start = new CountDownLatch(1);
    try (var pool = Executors.newFixedThreadPool(2)) {
      var first =
          pool.submit(
              () -> {
                start.await();
                service.recordDiscoveredPayments(
                    listRequest("list-" + RUN_A + "-1", "afp-" + RUN_A + "-1", "c1"), listResult("pay-1", "PENDING"));
                return null;
              });
      var second =
          pool.submit(
              () -> {
                start.await();
                service.recordDiscoveredPayments(
                    listRequest("list-" + RUN_B + "-1", "afp-" + RUN_B + "-1", "c2"), listResult("pay-1", "PAID"));
                return null;
              });
      start.countDown();
      first.get(10, TimeUnit.SECONDS);
      second.get(10, TimeUnit.SECONDS);
    }
    String payment = MonitorProjectionIds.payment(COMPANY, "pay-1");
    assertEquals(1, jdbc.queryForObject("select count(*) from tb_monitor_projection where record_id = ?", Integer.class, payment));
    assertEquals("PAID", store.findById(payment).orElseThrow().financialState());
  }

  @Test
  void retentionPurgeUsesClockAndKeepsValidRows() {
    JdbcTemplate jdbc = jdbc("spider_monitor_retention");
    new MonitorSchemaMigrator(jdbc).migrate();
    Instant now = Instant.parse("2026-10-13T12:00:00Z");
    JdbcMonitorProjectionStoreAdapter store = new JdbcMonitorProjectionStoreAdapter(jdbc);
    MonitorProjectionService service = new MonitorProjectionService(store, Duration.ofDays(90), Clock.fixed(now, ZoneOffset.UTC));
    service.touchInteraction(
        lookupRequest("keep-me", "ext-keep"),
        OperationalEventType.SATELLITE_RESPONSE_RETURNED,
        OperationalEventOutcome.SUCCESS,
        "READY");
    jdbc.update(
        "update tb_monitor_projection set retention_until = ? where record_id = ?",
        java.sql.Timestamp.from(now.minusSeconds(1)),
        MonitorProjectionIds.interaction(lookupRequest("keep-me", "ext-keep")));
    service.touchInteraction(
        lookupRequest("still-valid", "ext-valid"),
        OperationalEventType.SATELLITE_RESPONSE_RETURNED,
        OperationalEventOutcome.SUCCESS,
        "READY");
    assertEquals(1, service.purgeExpired());
    assertTrue(store.findById(MonitorProjectionIds.interaction(lookupRequest("still-valid", "ext-valid"))).isPresent());
    assertTrue(
        store.search(null, null, null, now, 20, null, null).stream()
            .noneMatch(item -> "keep-me".equals(item.messageId())));
  }

  private static void waitUntilReady() throws Exception {
    for (int i = 0; i < 40; i++) {
      try {
        jdbc().execute("select 1");
        return;
      } catch (Exception ignored) {
        Thread.sleep(500);
      }
    }
    throw new IllegalStateException("PostgreSQL 16 did not become ready");
  }

  private static JdbcTemplate jdbc() {
    return jdbc("spider_monitor");
  }

  private static JdbcTemplate jdbc(String database) {
    if (!"spider_monitor".equals(database)) {
      JdbcTemplate admin = new JdbcTemplate(dataSource("spider_monitor"));
      Integer exists =
          admin.queryForObject("select count(*) from pg_database where datname = ?", Integer.class, database);
      if (exists == null || exists == 0) {
        admin.execute("create database " + database);
      }
    }
    return new JdbcTemplate(dataSource(database));
  }

  private static DriverManagerDataSource dataSource(String database) {
    DriverManagerDataSource dataSource = new DriverManagerDataSource();
    dataSource.setUrl("jdbc:postgresql://127.0.0.1:" + PORT + "/" + database);
    dataSource.setUsername("spider");
    dataSource.setPassword("spider");
    dataSource.setDriverClassName("org.postgresql.Driver");
    return dataSource;
  }

  private static int historyCount(JdbcTemplate jdbc) {
    Integer count = jdbc.queryForObject("select count(*) from tb_monitor_schema_history", Integer.class);
    return count == null ? 0 : count;
  }

  private static String read(String version) {
    try {
      return new String(
          MonitorSchemaMigrator.class.getClassLoader().getResourceAsStream("db/monitor/" + version).readAllBytes(),
          java.nio.charset.StandardCharsets.UTF_8);
    } catch (Exception e) {
      throw new IllegalStateException(e);
    }
  }

  private static int exec(String... command) throws Exception {
    Process process = new ProcessBuilder(command).redirectErrorStream(true).start();
    process.getInputStream().transferTo(System.out);
    return process.waitFor();
  }

  private static ExecutionResult listResult(String transactionId, String status) {
    return new ExecutionResult(
        true,
        "COMPLETED",
        "preq-1",
        "actionhub-pay",
        "pref-1",
        "ACTIONHUB_PAY",
        "FINANCIAL_WATERMARK",
        List.of(),
        List.of(),
        Map.of(
            "companyId",
            COMPANY,
            "environment",
            "HOMOLOG",
            "items",
            List.of(Map.of("transactionId", transactionId, "normalizedStatus", status, "originalStatus", status))));
  }

  private static SatelliteInteractionRequest listRequest(String messageId, String correlationId, String idempotency) {
    String now = "2026-10-13T12:00:00Z";
    return new SatelliteInteractionRequest(
        "1.4",
        messageId,
        correlationId,
        "actionfinance",
        "EXPERIENCE",
        "QUERY_STATUS",
        now,
        idempotency,
        "FINANCIAL_EXTERNAL_LIST",
        new Objective("LIST_EXTERNAL_PAYMENTS", "SATELLITE_GOVERNED", now),
        new ContextBlock(
            null,
            new ContextSnapshot(
                "1.4",
                "INTERNAL",
                true,
                new Provenance("SATELLITE_GOVERNED", "ACTIONFINANCE_FINANCIAL_LIST_V1", now, "SERVER_REGISTRY", "GOVERNED"),
                Map.of("channel", "ACTIONFINANCE_HOMOLOG", "companyId", COMPANY),
                List.of(),
                "GOVERNED_SOURCE")),
        "INTERNAL",
        "SYNC",
        Map.of(),
        Map.of("financialList", Map.of("companyId", COMPANY, "environment", "HOMOLOG", "originSystem", "ACTIONHUB_PAY")));
  }

  private static SatelliteInteractionRequest lookupRequest(String messageId, String reference) {
    String now = "2026-10-13T12:00:00Z";
    return new SatelliteInteractionRequest(
        "1.3",
        messageId,
        "afc-" + messageId,
        "actionfinance",
        "EXPERIENCE",
        "QUERY_STATUS",
        now,
        "lookup:" + COMPANY + ":" + reference,
        "FINANCIAL_EXTERNAL_LOOKUP",
        new Objective("LOOKUP_EXTERNAL_PAYMENT", "SATELLITE_GOVERNED", now),
        new ContextBlock(
            null,
            new ContextSnapshot(
                "1.3",
                "INTERNAL",
                true,
                new Provenance("SATELLITE_GOVERNED", "ACTIONFINANCE_FINANCIAL_LOOKUP_V1", now, "SERVER_REGISTRY", "GOVERNED"),
                Map.of("channel", "ACTIONFINANCE_HOMOLOG", "companyId", COMPANY),
                List.of(),
                "GOVERNED_SOURCE")),
        "INTERNAL",
        "SYNC",
        Map.of(),
        Map.of("financialLookup", Map.of("companyId", COMPANY, "externalReference", reference, "originSystem", "ACTIONHUB_PAY")));
  }
}
