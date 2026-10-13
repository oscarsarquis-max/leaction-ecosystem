package br.com.banco.spider.operational.monitor;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.infrastructure.persistence.jdbc.JdbcMonitorProjectionStoreAdapter;
import br.com.banco.spider.infrastructure.persistence.jdbc.MonitorSchemaMigrator;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventType;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextBlock;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextSnapshot;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Objective;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Provenance;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.h2.jdbcx.JdbcDataSource;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

class MonitorProjectionJdbcRestartTest {

  private static final String COMPANY = "11111111-1111-4111-a111-111111111111";
  private static final String RUN = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";

  @Test
  void fileDatabaseSurvivesNewProcessEquivalentRestart() throws Exception {
    Path file = Files.createTempFile("spider-monitor", ".mv.db");
    Files.deleteIfExists(file);
    String url = "jdbc:h2:file:" + file.toAbsolutePath().toString().replace(".mv.db", "") + ";MODE=PostgreSQL";
    JdbcDataSource dataSource = new JdbcDataSource();
    dataSource.setURL(url);
    dataSource.setUser("sa");
    dataSource.setPassword("");
    JdbcTemplate jdbc = new JdbcTemplate(dataSource);
    new MonitorSchemaMigrator(jdbc).migrate();
    JdbcMonitorProjectionStoreAdapter first = new JdbcMonitorProjectionStoreAdapter(jdbc);
    MonitorProjectionService service = new MonitorProjectionService(first);
    SatelliteInteractionRequest request = listRequest();
    service.touchInteraction(
        request, OperationalEventType.SATELLITE_RESPONSE_RETURNED, OperationalEventOutcome.SUCCESS, "READY");
    String syncId = MonitorProjectionIds.sync(COMPANY, "HOMOLOG", RUN);
    assertTrue(first.findById(syncId).isPresent());
    JdbcMonitorProjectionStoreAdapter restarted = new JdbcMonitorProjectionStoreAdapter(new JdbcTemplate(dataSource));
    new MonitorSchemaMigrator(new JdbcTemplate(dataSource)).migrate();
    assertEquals("COMPLETED", restarted.findById(syncId).orElseThrow().technicalState());
    assertTrue(restarted.isDurable());
    Files.deleteIfExists(file);
    Files.deleteIfExists(Path.of(file.toString().replace(".mv.db", ".trace.db")));
  }

  private static SatelliteInteractionRequest listRequest() {
    String now = "2026-10-13T12:00:00Z";
    return new SatelliteInteractionRequest(
        "1.4",
        "list-" + RUN + "-1",
        "afp-" + RUN + "-1",
        "actionfinance",
        "EXPERIENCE",
        "QUERY_STATUS",
        now,
        "idemp-restart",
        "FINANCIAL_EXTERNAL_LIST",
        new Objective("LIST_EXTERNAL_PAYMENTS", "SATELLITE_GOVERNED", now),
        new ContextBlock(
            null,
            new ContextSnapshot(
                "1.4",
                "INTERNAL",
                true,
                new Provenance("SATELLITE_GOVERNED", "ACTIONFINANCE_FINANCIAL_LIST_V1", now, "SERVER_REGISTRY", "GOVERNED"),
                Map.of("companyId", COMPANY),
                java.util.List.of(),
                "GOVERNED_SOURCE")),
        "INTERNAL",
        "SYNC",
        Map.of(),
        Map.of("financialList", Map.of("companyId", COMPANY, "environment", "HOMOLOG", "originSystem", "ACTIONHUB_PAY")));
  }
}
