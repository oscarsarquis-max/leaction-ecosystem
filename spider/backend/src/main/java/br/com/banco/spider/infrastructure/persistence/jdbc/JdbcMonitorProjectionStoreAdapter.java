package br.com.banco.spider.infrastructure.persistence.jdbc;

import br.com.banco.spider.operational.monitor.MonitorProjectionMerge;
import br.com.banco.spider.operational.monitor.MonitorProjectionPort;
import br.com.banco.spider.operational.monitor.MonitorProjectionRecord;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.annotation.Transactional;

public class JdbcMonitorProjectionStoreAdapter implements MonitorProjectionPort {

  private final JdbcTemplate jdbc;

  public JdbcMonitorProjectionStoreAdapter(JdbcTemplate jdbc) {
    this.jdbc = jdbc;
  }

  @Override
  @Transactional
  public void upsert(MonitorProjectionRecord record) {
    if (record == null || record.recordId() == null || record.recordId().isBlank()) {
      return;
    }
    MonitorProjectionRecord merged =
        MonitorProjectionMerge.apply(findByIdIncludingExpired(record.recordId()).orElse(null), record);
    int updated = jdbc.update(UPDATE_SQL, params(merged, false));
    if (updated > 0) {
      return;
    }
    try {
      jdbc.update(INSERT_SQL, params(merged, true));
    } catch (DuplicateKeyException ignored) {
      MonitorProjectionRecord latest = findByIdIncludingExpired(record.recordId()).orElse(merged);
      jdbc.update(UPDATE_SQL, params(MonitorProjectionMerge.apply(latest, record), false));
    }
  }

  private static final String INSERT_SQL =
      """
      insert into tb_monitor_projection (
        record_id, kind, satellite_id, satellite_role, origin, message_id, correlation_id, execution_id,
        external_ref, capability, contract_version, company_id, environment, technical_state,
        commercial_state, financial_state, credit_state, current_component, objective, created_at,
        updated_at, last_synced_at, discovery_origin, event_key, projection_version, retention_until,
        sync_run_id, related_sync_id, related_payment_id, related_interaction_id, pages_consulted,
        found_count, new_count, updated_count, ignored_count, failed_count)
      values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
      """;

  private static final String UPDATE_SQL =
      """
      update tb_monitor_projection set
        kind=?, satellite_id=?, satellite_role=?, origin=?, message_id=?, correlation_id=?, execution_id=?,
        external_ref=?, capability=?, contract_version=?, company_id=?, environment=?, technical_state=?,
        commercial_state=?, financial_state=?, credit_state=?, current_component=?, objective=?, created_at=?,
        updated_at=?, last_synced_at=?, discovery_origin=?, event_key=?, projection_version=?, retention_until=?,
        sync_run_id=?, related_sync_id=?, related_payment_id=?, related_interaction_id=?, pages_consulted=?,
        found_count=?, new_count=?, updated_count=?, ignored_count=?, failed_count=?
      where record_id=?
      """;

  private static Object[] params(MonitorProjectionRecord merged, boolean insert) {
    Object[] values = {
      merged.kind(),
      merged.satelliteId(),
      merged.satelliteRole(),
      merged.origin(),
      merged.messageId(),
      merged.correlationId(),
      merged.executionId(),
      merged.externalRef(),
      merged.capability(),
      merged.contractVersion(),
      merged.companyId(),
      merged.environment(),
      merged.technicalState(),
      merged.commercialState(),
      merged.financialState(),
      merged.creditState(),
      merged.currentComponent(),
      merged.objective(),
      ts(merged.createdAt()),
      ts(merged.updatedAt()),
      ts(merged.lastSyncedAt()),
      merged.discoveryOrigin(),
      merged.eventKey(),
      merged.projectionVersion(),
      ts(merged.retentionUntil()),
      merged.syncRunId(),
      merged.relatedSyncId(),
      merged.relatedPaymentId(),
      merged.relatedInteractionId(),
      merged.pagesConsulted(),
      merged.foundCount(),
      merged.newCount(),
      merged.updatedCount(),
      merged.ignoredCount(),
      merged.failedCount()
    };
    if (insert) {
      Object[] withId = new Object[values.length + 1];
      withId[0] = merged.recordId();
      System.arraycopy(values, 0, withId, 1, values.length);
      return withId;
    }
    Object[] withId = new Object[values.length + 1];
    System.arraycopy(values, 0, withId, 0, values.length);
    withId[values.length] = merged.recordId();
    return withId;
  }

  @Override
  public Optional<MonitorProjectionRecord> findById(String recordId) {
    return findByIdIncludingExpired(recordId).filter(item -> !expired(item, Instant.now()));
  }

  @Override
  public List<MonitorProjectionRecord> search(
      String query, String origin, String kind, Instant now, int limit, Instant cursorUpdatedAt, String cursorId) {
    Instant clock = now == null ? Instant.now() : now;
    List<Object> args = new ArrayList<>();
    StringBuilder sql = new StringBuilder(
        """
        select * from tb_monitor_projection
        where retention_until > ?
        """);
    args.add(ts(clock));
    if (kind != null && !kind.isBlank()) {
      sql.append(" and kind = ?");
      args.add(kind);
    }
    if (origin != null && !origin.isBlank()) {
      sql.append(" and (lower(origin) = lower(?) or lower(satellite_id) = lower(?))");
      args.add(origin);
      args.add(origin);
    }
    if (query != null && !query.isBlank()) {
      String like = "%" + query.trim().toLowerCase(Locale.ROOT) + "%";
      sql.append(
          """
           and (
             lower(record_id) like ? or lower(coalesce(message_id,'')) like ?
             or lower(coalesce(correlation_id,'')) like ? or lower(coalesce(satellite_id,'')) like ?
             or lower(coalesce(company_id,'')) like ? or lower(coalesce(external_ref,'')) like ?
             or lower(coalesce(objective,'')) like ? or lower(coalesce(event_key,'')) like ?
             or lower(coalesce(sync_run_id,'')) like ? or lower(coalesce(related_sync_id,'')) like ?
             or lower(coalesce(related_payment_id,'')) like ?
           )
          """);
      for (int i = 0; i < 11; i++) {
        args.add(like);
      }
    }
    if (cursorUpdatedAt != null) {
      sql.append(" and (updated_at < ? or (updated_at = ? and record_id < ?))");
      args.add(ts(cursorUpdatedAt));
      args.add(ts(cursorUpdatedAt));
      args.add(cursorId);
    }
    sql.append(" order by updated_at desc, record_id desc limit ?");
    args.add(Math.max(1, limit));
    return jdbc.query(sql.toString(), this::map, args.toArray());
  }

  @Override
  @Transactional
  public int purgeExpired(Instant now) {
    Instant clock = now == null ? Instant.now() : now;
    return jdbc.update("delete from tb_monitor_projection where retention_until <= ?", ts(clock));
  }

  @Override
  public boolean isDurable() {
    return true;
  }

  private Optional<MonitorProjectionRecord> findByIdIncludingExpired(String recordId) {
    if (recordId == null || recordId.isBlank()) {
      return Optional.empty();
    }
    List<MonitorProjectionRecord> found =
        jdbc.query("select * from tb_monitor_projection where record_id = ?", this::map, recordId);
    return found.stream().findFirst();
  }

  private MonitorProjectionRecord map(ResultSet rs, int rowNum) throws SQLException {
    return MonitorProjectionRecord.builder()
        .recordId(rs.getString("record_id"))
        .kind(rs.getString("kind"))
        .satelliteId(rs.getString("satellite_id"))
        .satelliteRole(rs.getString("satellite_role"))
        .origin(rs.getString("origin"))
        .messageId(rs.getString("message_id"))
        .correlationId(rs.getString("correlation_id"))
        .executionId(rs.getString("execution_id"))
        .externalRef(rs.getString("external_ref"))
        .capability(rs.getString("capability"))
        .contractVersion(rs.getString("contract_version"))
        .companyId(rs.getString("company_id"))
        .environment(rs.getString("environment"))
        .technicalState(rs.getString("technical_state"))
        .commercialState(rs.getString("commercial_state"))
        .financialState(rs.getString("financial_state"))
        .creditState(rs.getString("credit_state"))
        .currentComponent(rs.getString("current_component"))
        .objective(rs.getString("objective"))
        .createdAt(instant(rs, "created_at"))
        .updatedAt(instant(rs, "updated_at"))
        .lastSyncedAt(instant(rs, "last_synced_at"))
        .discoveryOrigin(rs.getString("discovery_origin"))
        .eventKey(rs.getString("event_key"))
        .projectionVersion(rs.getInt("projection_version"))
        .retentionUntil(instant(rs, "retention_until"))
        .syncRunId(rs.getString("sync_run_id"))
        .relatedSyncId(rs.getString("related_sync_id"))
        .relatedPaymentId(rs.getString("related_payment_id"))
        .relatedInteractionId(rs.getString("related_interaction_id"))
        .pagesConsulted((Integer) rs.getObject("pages_consulted"))
        .foundCount((Integer) rs.getObject("found_count"))
        .newCount((Integer) rs.getObject("new_count"))
        .updatedCount((Integer) rs.getObject("updated_count"))
        .ignoredCount((Integer) rs.getObject("ignored_count"))
        .failedCount((Integer) rs.getObject("failed_count"))
        .build();
  }

  private static Instant instant(ResultSet rs, String column) throws SQLException {
    Timestamp value = rs.getTimestamp(column);
    return value == null ? null : value.toInstant();
  }

  private static Timestamp ts(Instant value) {
    return value == null ? null : Timestamp.from(value);
  }

  private static boolean expired(MonitorProjectionRecord item, Instant now) {
    return item.retentionUntil() != null && !item.retentionUntil().isAfter(now);
  }
}
