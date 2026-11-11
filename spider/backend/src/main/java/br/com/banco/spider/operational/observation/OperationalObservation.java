package br.com.banco.spider.operational.observation;

import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventType;
import br.com.banco.spider.satellite.application.SatelliteIdempotencyStore;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import javax.sql.DataSource;

/**
 * Fatos observáveis gravados no banco operacional. O Monitor não é chamado daqui.
 */
public final class OperationalObservation {

  private final DataSource dataSource;
  private final ObjectMapper mapper;

  public OperationalObservation(DataSource dataSource) {
    this.dataSource = dataSource;
    this.mapper = new ObjectMapper().configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
    migrate();
  }

  public void appendTouch(
      SatelliteInteractionRequest request,
      OperationalEventType type,
      OperationalEventOutcome outcome,
      String technicalState) {
    Map<String, Object> extra = new LinkedHashMap<>();
    extra.put("outcome", outcome == null ? "INFO" : outcome.name());
    append(request, "TOUCH", type == null ? "" : type.name(), technicalState, extra);
  }

  public void appendReplay(SatelliteInteractionRequest request) {
    append(request, "REPLAY", "REPLAY_CHECK_PASSED", "REPLAY_CHECK_PASSED", null);
  }

  public void appendPayments(SatelliteInteractionRequest request, ExecutionResult result) {
    Map<String, Object> extra = new LinkedHashMap<>();
    extra.put("available", result != null && result.available());
    extra.put("providerId", result == null ? null : result.providerId());
    extra.put("quote", result == null || result.quote() == null ? Map.of() : result.quote());
    append(request, "PAYMENTS", "PROVIDER_RESULT_RECEIVED", "PAYMENTS", extra);
  }

  public void rememberIdempotency(
      String satelliteId, String key, String fingerprint, Map<String, Object> response) {
    String sql =
        """
        INSERT INTO spider_satellite_idempotency (satellite_id, idempotency_key, fingerprint, response_json)
        VALUES (?, ?, ?, ?::jsonb)
        ON CONFLICT (satellite_id, idempotency_key) DO NOTHING
        """;
    try (Connection connection = dataSource.getConnection();
        PreparedStatement statement = connection.prepareStatement(sql)) {
      statement.setString(1, satelliteId);
      statement.setString(2, key);
      statement.setString(3, fingerprint);
      statement.setString(4, mapper.writeValueAsString(response));
      statement.executeUpdate();
    } catch (SQLException | JsonProcessingException exception) {
      throw new IllegalStateException("Não foi possível persistir a idempotência operacional.", exception);
    }
  }

  public SatelliteIdempotencyStore.Stored recallIdempotency(String satelliteId, String key) {
    String sql =
        """
        SELECT fingerprint, response_json::text
        FROM spider_satellite_idempotency
        WHERE satellite_id = ? AND idempotency_key = ?
        """;
    try (Connection connection = dataSource.getConnection();
        PreparedStatement statement = connection.prepareStatement(sql)) {
      statement.setString(1, satelliteId);
      statement.setString(2, key);
      try (ResultSet rows = statement.executeQuery()) {
        if (!rows.next()) {
          return null;
        }
        Map<String, Object> response = mapper.readValue(rows.getString(2), Map.class);
        return new SatelliteIdempotencyStore.Stored(rows.getString(1), response);
      }
    } catch (SQLException | JsonProcessingException exception) {
      throw new IllegalStateException("Não foi possível ler a idempotência operacional.", exception);
    }
  }

  public List<Fact> claim(int limit) {
    String sql =
        """
        WITH picked AS (
          SELECT id FROM spider_observation_outbox
          WHERE status IN ('PENDING', 'RETRY') AND available_at <= now() AND attempts < 12
          ORDER BY id
          FOR UPDATE SKIP LOCKED
          LIMIT ?
        )
        UPDATE spider_observation_outbox AS outbox
        SET status = 'CLAIMED', attempts = outbox.attempts + 1
        FROM picked
        WHERE outbox.id = picked.id
        RETURNING outbox.id, outbox.kind, outbox.aggregate_id, outbox.occurred_at, outbox.payload::text, outbox.attempts
        """;
    try (Connection connection = dataSource.getConnection()) {
      connection.setAutoCommit(false);
      try (PreparedStatement statement = connection.prepareStatement(sql)) {
        statement.setInt(1, limit);
        try (ResultSet rows = statement.executeQuery()) {
          List<Fact> facts = new ArrayList<>();
          while (rows.next()) {
            facts.add(
                new Fact(
                    rows.getLong(1),
                    rows.getString(2),
                    rows.getString(3),
                    rows.getTimestamp(4).toInstant(),
                    rows.getString(5),
                    rows.getInt(6)));
          }
          connection.commit();
          return facts;
        }
      } catch (SQLException exception) {
        connection.rollback();
        throw exception;
      }
    } catch (SQLException exception) {
      throw new IllegalStateException("Não foi possível reservar fatos do outbox.", exception);
    }
  }

  public void ack(long id) {
    updateStatus(id, "APPLIED", null, null);
  }

  public void retry(long id, int attempts, String error) {
    Instant available = Instant.now().plusSeconds(Math.min(60, attempts * 2L));
    String status = attempts >= 12 ? "DEAD" : "RETRY";
    updateStatus(id, status, available, error == null ? "" : error.substring(0, Math.min(500, error.length())));
  }

  public int pending() {
    return count("status IN ('PENDING','RETRY','CLAIMED')");
  }

  public int dead() {
    return count("status = 'DEAD'");
  }

  public Instant oldestPendingAt() {
    String sql =
        "SELECT min(occurred_at) FROM spider_observation_outbox WHERE status IN ('PENDING','RETRY','CLAIMED')";
    try (Connection connection = dataSource.getConnection();
        PreparedStatement statement = connection.prepareStatement(sql);
        ResultSet rows = statement.executeQuery()) {
      if (!rows.next() || rows.getTimestamp(1) == null) {
        return null;
      }
      return rows.getTimestamp(1).toInstant();
    } catch (SQLException exception) {
      throw new IllegalStateException("Não foi possível medir o atraso do outbox.", exception);
    }
  }

  private void append(
      SatelliteInteractionRequest request,
      String kind,
      String eventType,
      String technicalState,
      Map<String, Object> extra) {
    if (request == null || request.messageId() == null) {
      return;
    }
    Instant occurredAt = Instant.now();
    Map<String, Object> payload = new LinkedHashMap<>();
    payload.put("kind", kind);
    payload.put("eventType", eventType);
    payload.put("technicalState", technicalState);
    payload.put("request", request);
    if (extra != null) {
      payload.putAll(extra);
    }
    String factKey = sha256(request.messageId() + "|" + kind + "|" + eventType + "|" + String.valueOf(technicalState));
    String sql =
        """
        INSERT INTO spider_observation_outbox (fact_key, kind, aggregate_id, occurred_at, payload)
        VALUES (?, ?, ?, ?, ?::jsonb)
        ON CONFLICT (fact_key) DO NOTHING
        """;
    try (Connection connection = dataSource.getConnection();
        PreparedStatement statement = connection.prepareStatement(sql)) {
      statement.setString(1, factKey);
      statement.setString(2, kind);
      statement.setString(3, request.messageId());
      statement.setTimestamp(4, Timestamp.from(occurredAt));
      statement.setString(5, mapper.writeValueAsString(payload));
      statement.executeUpdate();
    } catch (SQLException | JsonProcessingException exception) {
      throw new IllegalStateException("Não foi possível gravar o fato operacional.", exception);
    }
  }

  private void updateStatus(long id, String status, Instant availableAt, String error) {
    String sql =
        """
        UPDATE spider_observation_outbox
        SET status = ?, available_at = COALESCE(?, available_at), last_error = ?, applied_at = CASE WHEN ? = 'APPLIED' THEN now() ELSE applied_at END
        WHERE id = ?
        """;
    try (Connection connection = dataSource.getConnection();
        PreparedStatement statement = connection.prepareStatement(sql)) {
      statement.setString(1, status);
      if (availableAt == null) {
        statement.setTimestamp(2, null);
      } else {
        statement.setTimestamp(2, Timestamp.from(availableAt));
      }
      statement.setString(3, error);
      statement.setString(4, status);
      statement.setLong(5, id);
      statement.executeUpdate();
    } catch (SQLException exception) {
      throw new IllegalStateException("Não foi possível atualizar o outbox.", exception);
    }
  }

  private int count(String where) {
    String sql = "SELECT count(*) FROM spider_observation_outbox WHERE " + where;
    try (Connection connection = dataSource.getConnection();
        PreparedStatement statement = connection.prepareStatement(sql);
        ResultSet rows = statement.executeQuery()) {
      rows.next();
      return rows.getInt(1);
    } catch (SQLException exception) {
      throw new IllegalStateException("Não foi possível contar o outbox.", exception);
    }
  }

  private void migrate() {
    String sql =
        """
        CREATE TABLE IF NOT EXISTS spider_observation_outbox (
          id BIGSERIAL PRIMARY KEY,
          fact_key TEXT NOT NULL UNIQUE,
          kind TEXT NOT NULL,
          aggregate_id TEXT NOT NULL,
          occurred_at TIMESTAMPTZ NOT NULL,
          payload JSONB NOT NULL,
          status TEXT NOT NULL DEFAULT 'PENDING',
          attempts INTEGER NOT NULL DEFAULT 0,
          available_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          last_error TEXT,
          applied_at TIMESTAMPTZ
        );
        CREATE TABLE IF NOT EXISTS spider_satellite_idempotency (
          satellite_id TEXT NOT NULL,
          idempotency_key TEXT NOT NULL,
          fingerprint TEXT NOT NULL,
          response_json JSONB NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          PRIMARY KEY (satellite_id, idempotency_key)
        );
        """;
    try (Connection connection = dataSource.getConnection();
        PreparedStatement statement = connection.prepareStatement(sql)) {
      statement.execute();
    } catch (SQLException exception) {
      throw new IllegalStateException("Não foi possível preparar o outbox operacional.", exception);
    }
  }

  private static String sha256(String value) {
    try {
      return HexFormat.of()
          .formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException exception) {
      throw new IllegalStateException(exception);
    }
  }

  public record Fact(long id, String kind, String aggregateId, Instant occurredAt, String payload, int attempts) {}
}
