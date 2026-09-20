package br.com.segsense.infrastructure.urlcapture;

import br.com.segsense.application.urlcapture.UrlCaptureConfirmationRecord;
import br.com.segsense.application.urlcapture.UrlCaptureRecord;
import br.com.segsense.application.urlcapture.UrlCaptureRepository;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class JdbcUrlCaptureRepository implements UrlCaptureRepository {

  private final JdbcTemplate jdbc;

  public JdbcUrlCaptureRepository(JdbcTemplate jdbc) {
    this.jdbc = jdbc;
  }

  @Override
  public void insertCapture(UrlCaptureRecord record) {
    jdbc.update(
        """
        INSERT INTO segsense.demo_url_capture (
          id, requested_url, final_url, final_host, captured_at, http_status, content_type,
          title, detected_language, excerpt, normalized_text, bytes_sha256, text_sha256,
          extractor_version, result_code, extracted_elements_json, correlation_id, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        record.id(),
        record.requestedUrl(),
        record.finalUrl(),
        record.finalHost(),
        Timestamp.from(record.capturedAt()),
        record.httpStatus(),
        record.contentType(),
        record.title(),
        record.detectedLanguage(),
        record.excerpt(),
        record.normalizedText(),
        record.bytesSha256(),
        record.textSha256(),
        record.extractorVersion(),
        record.resultCode(),
        record.extractedElementsJson(),
        record.correlationId(),
        Timestamp.from(record.createdAt()));
  }

  @Override
  public Optional<UrlCaptureRecord> findCapture(UUID id) {
    List<UrlCaptureRecord> rows =
        jdbc.query(
            """
            SELECT id, requested_url, final_url, final_host, captured_at, http_status, content_type,
                   title, detected_language, excerpt, normalized_text, bytes_sha256, text_sha256,
                   extractor_version, result_code, extracted_elements_json, correlation_id, created_at
              FROM segsense.demo_url_capture WHERE id = ?
            """,
            (rs, rowNum) -> mapCapture(rs),
            id);
    return rows.stream().findFirst();
  }

  @Override
  public void insertConfirmation(UrlCaptureConfirmationRecord record) {
    jdbc.update(
        """
        INSERT INTO segsense.demo_url_capture_confirmation (
          id, capture_id, confirmed_at, confirmed_elements_json, corrections_json, correlation_id)
        VALUES (?,?,?,?,?,?)
        """,
        record.id(),
        record.captureId(),
        Timestamp.from(record.confirmedAt()),
        record.confirmedElementsJson(),
        record.correctionsJson(),
        record.correlationId());
  }

  @Override
  public Optional<UrlCaptureConfirmationRecord> findLatestConfirmation(UUID captureId) {
    List<UrlCaptureConfirmationRecord> rows =
        jdbc.query(
            """
            SELECT id, capture_id, confirmed_at, confirmed_elements_json, corrections_json, correlation_id
              FROM segsense.demo_url_capture_confirmation
             WHERE capture_id = ?
             ORDER BY confirmed_at DESC
             LIMIT 1
            """,
            (rs, rowNum) -> mapConfirmation(rs),
            captureId);
    return rows.stream().findFirst();
  }

  @Override
  public List<UrlCaptureConfirmationRecord> confirmationsOf(UUID captureId) {
    return jdbc.query(
        """
        SELECT id, capture_id, confirmed_at, confirmed_elements_json, corrections_json, correlation_id
          FROM segsense.demo_url_capture_confirmation
         WHERE capture_id = ?
         ORDER BY confirmed_at ASC
        """,
        (rs, rowNum) -> mapConfirmation(rs),
        captureId);
  }

  private static UrlCaptureRecord mapCapture(ResultSet rs) throws SQLException {
    return new UrlCaptureRecord(
        rs.getObject("id", UUID.class),
        rs.getString("requested_url"),
        rs.getString("final_url"),
        rs.getString("final_host"),
        instant(rs, "captured_at"),
        (Integer) rs.getObject("http_status"),
        rs.getString("content_type"),
        rs.getString("title"),
        rs.getString("detected_language"),
        rs.getString("excerpt"),
        rs.getString("normalized_text"),
        rs.getString("bytes_sha256"),
        rs.getString("text_sha256"),
        rs.getString("extractor_version"),
        rs.getString("result_code"),
        rs.getString("extracted_elements_json"),
        rs.getString("correlation_id"),
        instant(rs, "created_at"));
  }

  private static UrlCaptureConfirmationRecord mapConfirmation(ResultSet rs) throws SQLException {
    return new UrlCaptureConfirmationRecord(
        rs.getObject("id", UUID.class),
        rs.getObject("capture_id", UUID.class),
        instant(rs, "confirmed_at"),
        rs.getString("confirmed_elements_json"),
        rs.getString("corrections_json"),
        rs.getString("correlation_id"));
  }

  private static Instant instant(ResultSet rs, String column) throws SQLException {
    Timestamp value = rs.getTimestamp(column);
    return value == null ? null : value.toInstant();
  }
}
