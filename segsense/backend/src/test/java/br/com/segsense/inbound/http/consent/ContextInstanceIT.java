package br.com.segsense.inbound.http.consent;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import br.com.segsense.application.link.OpaqueTokenGenerator;
import br.com.segsense.infrastructure.security.CatalogAuthorities;
import br.com.segsense.infrastructure.security.ConsentAuthorities;
import br.com.segsense.infrastructure.security.LinkAuthorities;
import br.com.segsense.infrastructure.security.OpportunityAuthorities;
import br.com.segsense.infrastructure.security.PublicationAuthorities;
import br.com.segsense.testsupport.MutableClock;
import com.jayway.jsonpath.JsonPath;
import java.time.Instant;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
@Testcontainers
@ActiveProfiles("test")
class ContextInstanceIT {

  private static final Instant FIXED = Instant.parse("2026-09-04T12:00:00Z");

  @Container
  @ServiceConnection
  static PostgreSQLContainer postgres = new PostgreSQLContainer("postgres:18.6");

  @Autowired MockMvc mockMvc;
  @Autowired JdbcTemplate jdbcTemplate;
  @Autowired MutableClock clock;

  @TestConfiguration
  static class Fixtures {
    @Bean
    @Primary
    MutableClock mutableClock() {
      return new MutableClock(FIXED);
    }

    @Bean
    @Primary
    OpaqueTokenGenerator opaqueTokenGenerator() {
      AtomicInteger sequence = new AtomicInteger();
      return () -> {
        String seed = "ins" + sequence.incrementAndGet() + "y".repeat(43);
        return seed.substring(0, 43);
      };
    }
  }

  @Test
  void createsNoticeInstanceAndProtectsEvidence() throws Exception {
    clock.setInstant(FIXED);
    Scope scope = seedActiveScope("cns-pub", "cns-ch", "cns-env");
    String base = opportunitiesUrl(scope);
    Published published = publishDynamic(scope, "crop-sense", base);
    String noticeUrl = published.path + "/consent-notice";

    mockMvc.perform(get(noticeUrl)).andExpect(status().isUnauthorized());
    mockMvc
        .perform(post(noticeUrl).with(writer()).contentType(MediaType.APPLICATION_JSON).content(noticePayload()))
        .andExpect(status().isCreated())
        .andExpect(jsonPath("$.status").value("DRAFT"));

    mockMvc
        .perform(
            post(noticeUrl + "/approve")
                .with(writer())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"expectedVersion\":0}"))
        .andExpect(status().isForbidden());

    mockMvc
        .perform(
            post(noticeUrl + "/approve")
                .with(approver())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"expectedVersion\":0}"))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.code").value("JUSTIFICATION_REQUIRED"));

    String approvedNotice =
        mockMvc
            .perform(
                post(noticeUrl + "/approve")
                    .with(approver())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(
                        "{\"expectedVersion\":0,\"justification\":\"Aprovar aviso para continuidade local no SegSense.\"}"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("APPROVED"))
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID noticeId = UUID.fromString(JsonPath.read(approvedNotice, "$.id"));
    long noticeVersion = ((Number) JsonPath.read(approvedNotice, "$.version")).longValue();

    String issued =
        mockMvc
            .perform(
                post(published.links)
                    .with(manager())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(issuePayload("artigo-continuacao-2026", "2026-10-01T00:00:00Z")))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();
    String token = JsonPath.read(issued, "$.token");

    mockMvc
        .perform(get("/api/v1/public/context-links/" + token))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.continuity.available").value(true))
        .andExpect(jsonPath("$.continuity.noticeVersion").value(1))
        .andExpect(jsonPath("$.continuity.purposeTitle").value("Uso no SegSense"))
        .andExpect(header().string("Cache-Control", "no-store"));

    String created =
        mockMvc
            .perform(
                post("/api/v1/public/context-links/" + token + "/context-instances")
                    .header("Idempotency-Key", "idempotency-key-once")
                    .contentType(MediaType.APPLICATION_JSON))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.instanceCredential").isString())
            .andExpect(jsonPath("$.sessionEndsOnReload").value(true))
            .andExpect(jsonPath("$.status").value("AWAITING_INPUT"))
            .andReturn()
            .getResponse()
            .getContentAsString();
    String credential = JsonPath.read(created, "$.instanceCredential");
    int version = ((Number) JsonPath.read(created, "$.expectedVersion")).intValue();

    mockMvc
        .perform(
            post("/api/v1/public/context-links/" + token + "/context-instances")
                .header("Idempotency-Key", "idempotency-key-once")
                .contentType(MediaType.APPLICATION_JSON))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.code").value("INSTANCE_CREDENTIAL_NOT_REPLAYABLE"))
        .andExpect(jsonPath("$.instanceCredential").doesNotExist())
        .andExpect(jsonPath("$.message").value(org.hamcrest.Matchers.containsString("nova chave")));

    mockMvc
        .perform(post("/api/v1/public/context-links/" + token + "/context-instances").contentType(MediaType.APPLICATION_JSON))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.code").value("IDEMPOTENCY_KEY_REQUIRED"));

    mockMvc
        .perform(
            post("/api/v1/public/context-links/" + token + "/context-instances")
                .header("Idempotency-Key", "short")
                .contentType(MediaType.APPLICATION_JSON))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.code").value("IDEMPOTENCY_KEY_INVALID"));

    mockMvc
        .perform(
            post("/api/v1/public/context-links/" + token + "/context-instances")
                .header("Origin", "http://evil.example")
                .contentType(MediaType.APPLICATION_JSON))
        .andExpect(status().isForbidden());

    mockMvc
        .perform(
            put("/api/v1/public/context-links/" + token + "/context-instances/current/values")
                .header("X-SegSense-Instance-Credential", credential)
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    "{\"expectedVersion\":"
                        + version
                        + ",\"values\":[{\"key\":\"comment\",\"type\":\"TEXT\",\"value\":\"nota de safra\"}]}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("AWAITING_DECISION"))
        .andExpect(jsonPath("$.instanceCredential").doesNotExist());

    version++;
    mockMvc
        .perform(
            post("/api/v1/public/context-links/" + token + "/context-instances/current/authorize")
                .header("X-SegSense-Instance-Credential", credential)
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"expectedVersion\":" + version + ",\"noticeVersion\":1,\"acknowledged\":true}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("AUTHORIZED"));

    version++;
    mockMvc
        .perform(
            post("/api/v1/public/context-links/" + token + "/context-instances/current/withdraw")
                .header("X-SegSense-Instance-Credential", credential)
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"expectedVersion\":" + version + "}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("AUTHORIZATION_WITHDRAWN"));

    assertThatThrownBy(() -> jdbcTemplate.update("UPDATE segsense.consent_decision SET actor = 'X'"))
        .hasMessageContaining("append-only");

    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    INSERT INTO segsense.context_instance_value
                    (id, instance_id, snapshot_id, opportunity_revision_id, field_key, field_type, field_source, classification, text_value)
                    SELECT ?, i.id, i.notice_snapshot_id, i.opportunity_revision_id, 'email', 'TEXT', 'USER', 'PERSONAL', 'a@b.c'
                    FROM segsense.context_instance i
                    WHERE i.status = 'AUTHORIZATION_WITHDRAWN'
                    LIMIT 1
                    """,
                    UUID.randomUUID()))
        .isInstanceOf(Exception.class);

    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    INSERT INTO segsense.context_instance_value
                    (id, instance_id, snapshot_id, opportunity_revision_id, field_key, field_type, field_source, classification, text_value)
                    SELECT ?, i.id, i.notice_snapshot_id, i.opportunity_revision_id, 'comment', 'TEXT', 'PUBLISHER', 'NON_PERSONAL', 'x'
                    FROM segsense.context_instance i
                    WHERE i.status = 'AUTHORIZATION_WITHDRAWN'
                    LIMIT 1
                    """,
                    UUID.randomUUID()))
        .isInstanceOf(Exception.class);

    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    INSERT INTO segsense.context_instance_value
                    (id, instance_id, snapshot_id, opportunity_revision_id, field_key, field_type, field_source, classification, number_value)
                    SELECT ?, i.id, i.notice_snapshot_id, i.opportunity_revision_id, 'comment', 'NUMBER', 'USER', 'NON_PERSONAL', 1
                    FROM segsense.context_instance i
                    WHERE i.status = 'AUTHORIZATION_WITHDRAWN'
                    LIMIT 1
                    """,
                    UUID.randomUUID()))
        .isInstanceOf(Exception.class);

    UUID rogueSnapshot = UUID.randomUUID();
    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    INSERT INTO segsense.consent_notice_snapshot
                    (id, notice_id, version_number, purpose_title, purpose_description, transparency_text,
                     no_external_sharing_text, content_hash, created_at, created_by, opportunity_revision_id)
                    SELECT ?, n.id, 99, s.purpose_title, s.purpose_description, s.transparency_text,
                           s.no_external_sharing_text, s.content_hash, NOW(), 'sql', n.opportunity_revision_id
                    FROM segsense.consent_notice n
                    JOIN segsense.consent_notice_snapshot s ON s.notice_id = n.id AND s.version_number = n.current_version
                    LIMIT 1
                    """,
                    rogueSnapshot))
        .hasMessageContaining("approved or retired");
    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    INSERT INTO segsense.context_instance_value
                    (id, instance_id, snapshot_id, opportunity_revision_id, field_key, field_type, field_source, classification, text_value)
                    SELECT ?, i.id, ?, i.opportunity_revision_id, 'comment', 'TEXT', 'USER', 'NON_PERSONAL', 'cruzado'
                    FROM segsense.context_instance i
                    WHERE i.status = 'AUTHORIZATION_WITHDRAWN'
                    LIMIT 1
                    """,
                    UUID.randomUUID(),
                    rogueSnapshot))
        .isInstanceOf(Exception.class);

    UUID otherRevision = UUID.randomUUID();
    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    INSERT INTO segsense.consent_notice_field
                    (id, snapshot_id, opportunity_revision_id, field_key, field_label, field_type, field_source, classification, required, position)
                    SELECT ?, s.id, ?, 'comment', 'Comentario', 'TEXT', 'USER', 'NON_PERSONAL', FALSE, 9
                    FROM segsense.consent_notice_snapshot s LIMIT 1
                    """,
                    UUID.randomUUID(),
                    otherRevision))
        .isInstanceOf(Exception.class);

    assertThatThrownBy(
            () -> jdbcTemplate.update("UPDATE segsense.consent_notice_snapshot SET purpose_title = 'alterado'"))
        .hasMessageContaining("append-only");
    assertThatThrownBy(() -> jdbcTemplate.update("DELETE FROM segsense.consent_notice_snapshot"))
        .hasMessageContaining("append-only");
    assertThatThrownBy(
            () -> jdbcTemplate.update("UPDATE segsense.consent_notice_field SET field_label = 'x'"))
        .hasMessageContaining("append-only");

    assertThat(
            jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM segsense.consent_notice_decision WHERE notice_id = ? AND decision_type = 'APPROVED'",
                Long.class,
                noticeId))
        .isEqualTo(1);
    String storedJustification =
        jdbcTemplate.queryForObject(
            "SELECT justification FROM segsense.consent_notice_decision WHERE notice_id = ? AND decision_type = 'APPROVED'",
            String.class,
            noticeId);
    assertThat(storedJustification).contains("Aprovar aviso");

    mockMvc
        .perform(
            post(noticeUrl + "/retire")
                .with(writer())
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    "{\"expectedVersion\":"
                        + noticeVersion
                        + ",\"justification\":\"Encerrar aviso apos evidencia local registrada.\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("RETIRED"));
    assertThat(
            jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM segsense.consent_notice_decision WHERE notice_id = ? AND decision_type = 'RETIRED'",
                Long.class,
                noticeId))
        .isEqualTo(1);

    long decisions =
        jdbcTemplate.queryForObject(
            """
            SELECT COUNT(*) FROM segsense.consent_decision d
            JOIN segsense.context_instance i ON d.instance_id = i.id
            WHERE i.notice_id = ?
            """,
            Long.class,
            noticeId);
    assertThat(decisions).isEqualTo(2);

    UUID approvedSnapshotId =
        jdbcTemplate.queryForObject(
            "SELECT notice_snapshot_id FROM segsense.context_instance WHERE notice_id = ?",
            UUID.class,
            noticeId);
    assertThatThrownBy(() -> insertRogueNoticeField(approvedSnapshotId))
        .hasMessageContaining("approved or retired");
    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    INSERT INTO segsense.consent_notice_snapshot
                    (id, notice_id, version_number, purpose_title, purpose_description, transparency_text,
                     no_external_sharing_text, content_hash, created_at, created_by, opportunity_revision_id)
                    SELECT ?, n.id, 98, s.purpose_title, s.purpose_description, s.transparency_text,
                           s.no_external_sharing_text, s.content_hash, NOW(), 'sql', n.opportunity_revision_id
                    FROM segsense.consent_notice n
                    JOIN segsense.consent_notice_snapshot s ON s.notice_id = n.id AND s.version_number = n.current_version
                    WHERE n.id = ?
                    """,
                    UUID.randomUUID(),
                    noticeId))
        .hasMessageContaining("approved or retired");
    String approvedHash =
        jdbcTemplate.queryForObject(
            """
            SELECT s.content_hash
            FROM segsense.consent_notice_snapshot s
            JOIN segsense.consent_notice n ON n.id = s.notice_id AND s.version_number = n.approved_version
            WHERE n.id = ?
            """,
            String.class,
            noticeId);
    String decisionHash =
        jdbcTemplate.queryForObject(
            "SELECT content_hash FROM segsense.consent_notice_decision WHERE notice_id = ? AND decision_type = 'APPROVED'",
            String.class,
            noticeId);
    assertThat(decisionHash).isEqualTo(approvedHash);
    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    "UPDATE segsense.consent_notice SET current_version = current_version + 1 WHERE id = ?",
                    noticeId))
        .hasMessageContaining("immutable");
  }

  @Test
  void freezesCommittedDraftFieldsAndAllowsNewDraftSnapshot() throws Exception {
    clock.setInstant(FIXED);
    Scope scope = seedActiveScope("cns-pub-d", "cns-ch-d", "cns-env-d");
    String base = opportunitiesUrl(scope);
    Published published = publishDynamic(scope, "crop-draft", base);
    String noticeUrl = published.path + "/consent-notice";
    String created =
        mockMvc
            .perform(post(noticeUrl).with(writer()).contentType(MediaType.APPLICATION_JSON).content(noticePayload()))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.status").value("DRAFT"))
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID noticeId = UUID.fromString(JsonPath.read(created, "$.id"));
    long expectedVersion = ((Number) JsonPath.read(created, "$.version")).longValue();
    UUID draftSnapshotId =
        jdbcTemplate.queryForObject(
            "SELECT id FROM segsense.consent_notice_snapshot WHERE notice_id = ? AND version_number = 1",
            UUID.class,
            noticeId);
    assertThatThrownBy(() -> insertRogueNoticeField(draftSnapshotId))
        .hasMessageContaining("committed notice snapshot");

    String drafted =
        mockMvc
            .perform(
                post(noticeUrl + "/draft")
                    .with(writer())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(
                        """
                        {"expectedVersion":%s,
                         "purposeTitle":"Uso no SegSense",
                         "purposeDescription":"Continuar esta jornada apenas no SegSense, sem envio externo.",
                         "transparencyText":"As informacoes desta etapa permanecem no SegSense e nao vao a seguradora.",
                         "noExternalSharingText":"Nao ha compartilhamento externo nesta etapa."}
                        """
                            .formatted(expectedVersion)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("DRAFT"))
            .andExpect(jsonPath("$.currentVersion").value(2))
            .andReturn()
            .getResponse()
            .getContentAsString();
    expectedVersion = ((Number) JsonPath.read(drafted, "$.version")).longValue();
    assertThat(
            jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM segsense.consent_notice_snapshot WHERE notice_id = ?",
                Long.class,
                noticeId))
        .isEqualTo(2);

    mockMvc
        .perform(
            post(noticeUrl + "/approve")
                .with(approver())
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    "{\"expectedVersion\":"
                        + expectedVersion
                        + ",\"justification\":\"Aprovar aviso para continuidade local no SegSense.\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("APPROVED"))
        .andExpect(jsonPath("$.approvedVersion").value(2));

    UUID approvedSnapshotId =
        jdbcTemplate.queryForObject(
            "SELECT id FROM segsense.consent_notice_snapshot WHERE notice_id = ? AND version_number = 2",
            UUID.class,
            noticeId);
    assertThatThrownBy(() -> insertRogueNoticeField(approvedSnapshotId))
        .hasMessageContaining("approved or retired");
    assertThatThrownBy(
            () -> jdbcTemplate.update("UPDATE segsense.consent_notice_field SET field_label = 'x'"))
        .hasMessageContaining("append-only");
    assertThatThrownBy(() -> jdbcTemplate.update("DELETE FROM segsense.consent_notice_field"))
        .hasMessageContaining("append-only");
  }

  @Test
  void concurrentIdempotencyCreatesAtMostOneSecretlessReplay() throws Exception {
    clock.setInstant(FIXED);
    Scope scope = seedActiveScope("cns-pub-c", "cns-ch-c", "cns-env-c");
    String base = opportunitiesUrl(scope);
    Published published = publishDynamic(scope, "crop-conc", base);
    String noticeUrl = published.path + "/consent-notice";
    mockMvc
        .perform(post(noticeUrl).with(writer()).contentType(MediaType.APPLICATION_JSON).content(noticePayload()))
        .andExpect(status().isCreated());
    mockMvc
        .perform(
            post(noticeUrl + "/approve")
                .with(approver())
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    "{\"expectedVersion\":0,\"justification\":\"Aprovar aviso para continuidade local no SegSense.\"}"))
        .andExpect(status().isOk());
    String issued =
        mockMvc
            .perform(
                post(published.links)
                    .with(manager())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(issuePayload("artigo-continuacao-conc", "2026-10-01T00:00:00Z")))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();
    String token = JsonPath.read(issued, "$.token");
    var first =
        mockMvc
            .perform(
                post("/api/v1/public/context-links/" + token + "/context-instances")
                    .header("Idempotency-Key", "idempotency-key-race")
                    .contentType(MediaType.APPLICATION_JSON))
            .andExpect(status().isCreated())
            .andReturn();
    var replay =
        mockMvc
            .perform(
                post("/api/v1/public/context-links/" + token + "/context-instances")
                    .header("Idempotency-Key", "idempotency-key-race")
                    .contentType(MediaType.APPLICATION_JSON))
            .andExpect(status().isConflict())
            .andExpect(jsonPath("$.code").value("INSTANCE_CREDENTIAL_NOT_REPLAYABLE"))
            .andReturn()
            .getResponse()
            .getContentAsString();
    assertThat(first.getResponse().getContentAsString()).contains("instanceCredential");
    assertThat(replay).doesNotContain("instanceCredential");
  }

  private void insertRogueNoticeField(UUID snapshotId) {
    String fieldKey = "plot" + UUID.randomUUID().toString().replace("-", "").substring(0, 8);
    jdbcTemplate.update(
        """
        INSERT INTO segsense.contextual_opportunity_revision_field
        (id, opportunity_revision_id, field_key, label, type, required, source, classification, position, allowed_values)
        SELECT ?, s.opportunity_revision_id, ?, 'Nota extra', 'TEXT', FALSE, 'USER', 'NON_PERSONAL',
               COALESCE((
                 SELECT MAX(f.position) + 1
                 FROM segsense.contextual_opportunity_revision_field f
                 WHERE f.opportunity_revision_id = s.opportunity_revision_id
               ), 0),
               NULL
        FROM segsense.consent_notice_snapshot s
        WHERE s.id = ?
        """,
        UUID.randomUUID(),
        fieldKey,
        snapshotId);
    Integer nextPosition =
        jdbcTemplate.queryForObject(
            """
            SELECT COALESCE(MAX(f.position), -1) + 1
            FROM segsense.consent_notice_field f
            WHERE f.snapshot_id = ?
            """,
            Integer.class,
            snapshotId);
    jdbcTemplate.update(
        """
        INSERT INTO segsense.consent_notice_field
        (id, snapshot_id, opportunity_revision_id, field_key, field_label, field_type, field_source, classification, required, position)
        SELECT ?, s.id, s.opportunity_revision_id, ?, 'Nota extra', 'TEXT', 'USER', 'NON_PERSONAL', FALSE, ?
        FROM segsense.consent_notice_snapshot s
        WHERE s.id = ?
        """,
        UUID.randomUUID(),
        fieldKey,
        nextPosition,
        snapshotId);
  }

  private static String noticePayload() {
    return """
        {"purposeTitle":"Uso no SegSense",
         "purposeDescription":"Continuar esta jornada apenas no SegSense, sem envio externo.",
         "transparencyText":"As informacoes desta etapa permanecem no SegSense e nao vao a seguradora.",
         "noExternalSharingText":"Nao ha compartilhamento externo nesta etapa."}
        """;
  }

  private Published publishDynamic(Scope scope, String key, String base) throws Exception {
    String created =
        mockMvc
            .perform(post(base).with(author()).contentType(MediaType.APPLICATION_JSON).content(dynamicPayload(key)))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID opportunityId = UUID.fromString(JsonPath.read(created, "$.id"));
    long version = ((Number) JsonPath.read(created, "$.version")).longValue();
    String path = base + "/" + opportunityId;
    mockMvc
        .perform(
            post(path + "/governance/submit")
                .with(author())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"expectedVersion\":" + version + "}"))
        .andExpect(status().isOk());
    version++;
    mockMvc
        .perform(
            post(path + "/governance/approve")
                .with(reviewer())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"expectedVersion\":" + version + ",\"revisionNumber\":1}"))
        .andExpect(status().isOk());
    version++;
    mockMvc
        .perform(
            post(path + "/publication/activate")
                .with(activator())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"expectedVersion\":" + version + "}"))
        .andExpect(status().isOk());
    return new Published(opportunityId, path, path + "/links", version + 1);
  }

  private Scope seedActiveScope(String publisherKey, String channelKey, String environmentKey)
      throws Exception {
    String publisherBody =
        mockMvc
            .perform(
                post("/api/v1/admin/publishers")
                    .with(operator())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("{\"key\":\"" + publisherKey + "\",\"name\":\"Publicador " + publisherKey + "\"}"))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID publisherId = UUID.fromString(JsonPath.read(publisherBody, "$.id"));
    long publisherVersion = ((Number) JsonPath.read(publisherBody, "$.version")).longValue();
    mockMvc
        .perform(
            post("/api/v1/admin/publishers/" + publisherId + "/status")
                .with(operator())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"ACTIVE\",\"version\":" + publisherVersion + "}"))
        .andExpect(status().isOk());
    String channelBody =
        mockMvc
            .perform(
                post("/api/v1/admin/publishers/" + publisherId + "/channels")
                    .with(operator())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(
                        "{\"key\":\"" + channelKey + "\",\"name\":\"Canal " + channelKey + "\",\"type\":\"WEBSITE\"}"))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID channelId = UUID.fromString(JsonPath.read(channelBody, "$.id"));
    long channelVersion = ((Number) JsonPath.read(channelBody, "$.version")).longValue();
    mockMvc
        .perform(
            post("/api/v1/admin/publishers/" + publisherId + "/channels/" + channelId + "/status")
                .with(operator())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"ACTIVE\",\"version\":" + channelVersion + "}"))
        .andExpect(status().isOk());
    String environmentBody =
        mockMvc
            .perform(
                post("/api/v1/admin/publishers/"
                        + publisherId
                        + "/channels/"
                        + channelId
                        + "/environments")
                    .with(operator())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(
                        "{\"key\":\""
                            + environmentKey
                            + "\",\"name\":\"Ambiente "
                            + environmentKey
                            + "\",\"type\":\"PAGE\"}"))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID environmentId = UUID.fromString(JsonPath.read(environmentBody, "$.id"));
    long environmentVersion = ((Number) JsonPath.read(environmentBody, "$.version")).longValue();
    mockMvc
        .perform(
            post("/api/v1/admin/publishers/"
                    + publisherId
                    + "/channels/"
                    + channelId
                    + "/environments/"
                    + environmentId
                    + "/status")
                .with(operator())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"ACTIVE\",\"version\":" + environmentVersion + "}"))
        .andExpect(status().isOk());
    return new Scope(publisherId, channelId, environmentId);
  }

  private static String opportunitiesUrl(Scope scope) {
    return "/api/v1/admin/publishers/"
        + scope.publisherId
        + "/channels/"
        + scope.channelId
        + "/environments/"
        + scope.environmentId
        + "/opportunities";
  }

  private static String dynamicPayload(String key) {
    return """
        {"key":"%s","title":"Protecao agricola xx","contextMode":"DYNAMIC",
         "contextSummaryTemplate":"Resumo para {{riskType}} no ambiente.",
         "objectiveTemplate":"Quero avaliar protecao neste contexto editorial.",
         "callToActionLabel":"Avaliar",
         "contextFields":[
           {"key":"riskType","label":"Tipo de risco","type":"ENUM","required":true,"source":"PUBLISHER","classification":"NON_PERSONAL","allowedValues":["quebra-safra","seca"]},
           {"key":"area","label":"Area plantada","type":"NUMBER","required":true,"source":"PUBLISHER","classification":"NON_PERSONAL"},
           {"key":"comment","label":"Comentario","type":"TEXT","required":false,"source":"USER","classification":"NON_PERSONAL"}
         ]}
        """
        .formatted(key);
  }

  private static String issuePayload(String placement, String expiresAt) {
    return """
        {"placementKey":"%s","label":"Artigo quebra de safra","expiresAt":"%s",
         "publisherContext":[
           {"fieldKey":"riskType","value":"quebra-safra"},
           {"fieldKey":"area","value":12.5}
         ]}
        """
        .formatted(placement, expiresAt);
  }

  private static RequestPostProcessor operator() {
    return user("operator")
        .authorities(
            new SimpleGrantedAuthority(CatalogAuthorities.READ),
            new SimpleGrantedAuthority(CatalogAuthorities.WRITE),
            new SimpleGrantedAuthority(OpportunityAuthorities.READ),
            new SimpleGrantedAuthority(OpportunityAuthorities.WRITE));
  }

  private static RequestPostProcessor author() {
    return user("author")
        .authorities(
            new SimpleGrantedAuthority(CatalogAuthorities.READ),
            new SimpleGrantedAuthority(OpportunityAuthorities.READ),
            new SimpleGrantedAuthority(OpportunityAuthorities.WRITE),
            new SimpleGrantedAuthority(OpportunityAuthorities.SUBMIT));
  }

  private static RequestPostProcessor reviewer() {
    return user("reviewer")
        .authorities(
            new SimpleGrantedAuthority(OpportunityAuthorities.READ),
            new SimpleGrantedAuthority(OpportunityAuthorities.REVIEW));
  }

  private static RequestPostProcessor activator() {
    return user("activator")
        .authorities(
            new SimpleGrantedAuthority(OpportunityAuthorities.READ),
            new SimpleGrantedAuthority(PublicationAuthorities.MANAGE));
  }

  private static RequestPostProcessor manager() {
    return user("link-manager")
        .authorities(
            new SimpleGrantedAuthority(LinkAuthorities.READ),
            new SimpleGrantedAuthority(LinkAuthorities.MANAGE));
  }

  private static RequestPostProcessor writer() {
    return user("notice-writer")
        .authorities(
            new SimpleGrantedAuthority(ConsentAuthorities.READ),
            new SimpleGrantedAuthority(ConsentAuthorities.WRITE));
  }

  private static RequestPostProcessor approver() {
    return user("notice-approver")
        .authorities(
            new SimpleGrantedAuthority(ConsentAuthorities.READ),
            new SimpleGrantedAuthority(ConsentAuthorities.APPROVE));
  }

  private record Scope(UUID publisherId, UUID channelId, UUID environmentId) {}

  private record Published(UUID opportunityId, String path, String links, long version) {}
}
