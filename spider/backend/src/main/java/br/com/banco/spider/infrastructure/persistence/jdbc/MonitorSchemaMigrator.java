package br.com.banco.spider.infrastructure.persistence.jdbc;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.sql.Connection;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import javax.sql.DataSource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.ConnectionCallback;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.util.StreamUtils;

public class MonitorSchemaMigrator {

  private static final Logger log = LoggerFactory.getLogger(MonitorSchemaMigrator.class);

  static final List<String> VERSIONS =
      List.of(
          "V20261013__tb_monitor_projection.sql",
          "V20261014__monitor_projection_links.sql",
          "V20261015__monitor_projection_correlation_index.sql");

  private static final long PG_LOCK_KEY = 88101316L;

  private final JdbcTemplate jdbc;

  public MonitorSchemaMigrator(JdbcTemplate jdbc) {
    this.jdbc = jdbc;
  }

  public void migrate() {
    DataSource dataSource = jdbc.getDataSource();
    if (dataSource == null) {
      throw new IllegalStateException("Migrator do Monitor exige um DataSource.");
    }
    TransactionTemplate tx = new TransactionTemplate(new DataSourceTransactionManager(dataSource));
    tx.executeWithoutResult(status -> {
      lockIfPostgres();
      ensureHistory();
      for (String version : VERSIONS) {
        apply(version);
      }
    });
  }

  private void lockIfPostgres() {
    jdbc.execute((ConnectionCallback<Void>) connection -> {
      if (isPostgreSql(connection)) {
        try (var statement = connection.createStatement()) {
          statement.execute("select pg_advisory_xact_lock(" + PG_LOCK_KEY + ")");
        }
      }
      return null;
    });
  }

  private void ensureHistory() {
    jdbc.execute(
        """
        create table if not exists tb_monitor_schema_history (
          version varchar(120) primary key,
          checksum varchar(64) not null,
          applied_at timestamp not null,
          status varchar(20) not null default 'SUCCESS'
        )
        """);
    jdbc.execute("alter table tb_monitor_schema_history add column if not exists status varchar(20)");
    jdbc.update("update tb_monitor_schema_history set status = 'SUCCESS' where status is null");
  }

  private void apply(String version) {
    String sql = read(version);
    String checksum = sha256(sql);
    List<HistoryRow> existing =
        jdbc.query(
            "select checksum, status from tb_monitor_schema_history where version = ?",
            (rs, row) -> new HistoryRow(rs.getString(1), rs.getString(2)),
            version);
    if (!existing.isEmpty()) {
      HistoryRow row = existing.getFirst();
      if (!"SUCCESS".equalsIgnoreCase(row.status())) {
        throw new IllegalStateException(
            "Migration do Monitor interrompida ou falha: " + version + " status=" + row.status());
      }
      if (!checksum.equals(row.checksum())) {
        throw new IllegalStateException("Checksum divergente da migration do Monitor: " + version);
      }
      if (projectionTableExists()) {
        return;
      }
      log.warn("event=monitor_schema_repair version={} reason=missing_projection_table", version);
      executeStatements(sql);
      return;
    }
    jdbc.update(
        "insert into tb_monitor_schema_history(version, checksum, applied_at, status) values (?,?,?,?)",
        version,
        checksum,
        java.sql.Timestamp.from(Instant.now()),
        "STARTED");
    executeStatements(sql);
    jdbc.update(
        "update tb_monitor_schema_history set status = 'SUCCESS', applied_at = ? where version = ?",
        java.sql.Timestamp.from(Instant.now()),
        version);
    log.info("event=monitor_schema_migrated version={}", version);
  }

  private void executeStatements(String sql) {
    for (String statement : sql.split(";")) {
      String trimmed = statement.trim();
      if (!trimmed.isEmpty()) {
        jdbc.execute(trimmed);
      }
    }
  }

  private boolean projectionTableExists() {
    Integer count =
        jdbc.queryForObject(
            """
            select count(*) from information_schema.tables
            where table_schema in ('public', current_schema())
              and lower(table_name) = 'tb_monitor_projection'
            """,
            Integer.class);
    return count != null && count > 0;
  }

  private static String read(String version) {
    try {
      ClassPathResource resource = new ClassPathResource("db/monitor/" + version);
      return StreamUtils.copyToString(resource.getInputStream(), StandardCharsets.UTF_8);
    } catch (Exception e) {
      throw new IllegalStateException("Migration do Monitor ausente: " + version, e);
    }
  }

  public static String sha256(String value) {
    try {
      return HexFormat.of()
          .formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException e) {
      throw new IllegalStateException(e);
    }
  }

  private static boolean isPostgreSql(Connection connection) {
    try {
      String product = connection.getMetaData().getDatabaseProductName();
      return product != null && product.toLowerCase(Locale.ROOT).contains("postgresql");
    } catch (Exception e) {
      return false;
    }
  }

  private record HistoryRow(String checksum, String status) {}
}
