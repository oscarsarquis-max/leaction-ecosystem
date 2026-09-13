package br.com.segsense.infrastructure.catalog;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

@SpringBootTest
@Testcontainers
@ActiveProfiles("test")
class CatalogScopeConstraintIT {

  @Container
  @ServiceConnection
  static PostgreSQLContainer postgres = new PostgreSQLContainer("postgres:18.6");

  @Autowired JdbcTemplate jdbcTemplate;

  @Test
  void flywayHasV3AndV4AndCompositeChannelFkRejectsCrossPublisher() {
    List<String> versions =
        jdbcTemplate.queryForList(
            "SELECT version FROM segsense.flyway_schema_history ORDER BY installed_rank",
            String.class);
    assertThat(versions).contains("1", "2", "3", "4", "5", "6");

    Integer unique =
        jdbcTemplate.queryForObject(
            """
            SELECT COUNT(*) FROM pg_constraint
            WHERE conname = 'channel_id_publisher_unique'
            """,
            Integer.class);
    Integer compositeFk =
        jdbcTemplate.queryForObject(
            """
            SELECT COUNT(*) FROM pg_constraint
            WHERE conname = 'environment_channel_scope_fk'
            """,
            Integer.class);
    Integer oldFk =
        jdbcTemplate.queryForObject(
            """
            SELECT COUNT(*) FROM pg_constraint
            WHERE conname = 'environment_channel_fk'
            """,
            Integer.class);
    assertThat(unique).isEqualTo(1);
    assertThat(compositeFk).isEqualTo(1);
    assertThat(oldFk).isZero();

    UUID publisherA = UUID.randomUUID();
    UUID publisherB = UUID.randomUUID();
    UUID channelA = UUID.randomUUID();
    insertPublisher(publisherA, "scope-pub-a");
    insertPublisher(publisherB, "scope-pub-b");
    insertChannel(channelA, publisherA, "scope-ch-a");

    UUID coherent = UUID.randomUUID();
    jdbcTemplate.update(
        """
        INSERT INTO segsense.contextual_environment
          (id, publisher_id, channel_id, key, name, type, status, version,
           created_at, updated_at, created_by, updated_by)
        VALUES (?, ?, ?, 'home-ok', 'Home coerente', 'PAGE', 'DRAFT', 0,
                NOW(), NOW(), 'it', 'it')
        """,
        coherent,
        publisherA,
        channelA);
    Map<String, Object> stored =
        jdbcTemplate.queryForMap(
            "SELECT publisher_id, channel_id FROM segsense.contextual_environment WHERE id = ?",
            coherent);
    assertThat(stored.get("publisher_id")).isEqualTo(publisherA);
    assertThat(stored.get("channel_id")).isEqualTo(channelA);

    UUID inconsistent = UUID.randomUUID();
    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    INSERT INTO segsense.contextual_environment
                      (id, publisher_id, channel_id, key, name, type, status, version,
                       created_at, updated_at, created_by, updated_by)
                    VALUES (?, ?, ?, 'home-bad', 'Home cruzado', 'PAGE', 'DRAFT', 0,
                            NOW(), NOW(), 'it', 'it')
                    """,
                    inconsistent,
                    publisherB,
                    channelA))
        .isInstanceOf(DataIntegrityViolationException.class);

    Integer leftover =
        jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM segsense.contextual_environment WHERE id = ?",
            Integer.class,
            inconsistent);
    assertThat(leftover).isZero();
  }

  private void insertPublisher(UUID id, String key) {
    jdbcTemplate.update(
        """
        INSERT INTO segsense.publisher
          (id, key, name, status, version, created_at, updated_at, created_by, updated_by)
        VALUES (?, ?, 'Publicador de prova', 'ACTIVE', 0, NOW(), NOW(), 'it', 'it')
        """,
        id,
        key);
  }

  private void insertChannel(UUID id, UUID publisherId, String key) {
    jdbcTemplate.update(
        """
        INSERT INTO segsense.channel
          (id, publisher_id, key, name, type, status, version,
           created_at, updated_at, created_by, updated_by)
        VALUES (?, ?, ?, 'Canal de prova', 'WEBSITE', 'ACTIVE', 0, NOW(), NOW(), 'it', 'it')
        """,
        id,
        publisherId,
        key);
  }
}
