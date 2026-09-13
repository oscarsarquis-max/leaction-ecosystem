package br.com.segsense.inbound.http.opportunity;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import br.com.segsense.infrastructure.security.CatalogAuthorities;
import br.com.segsense.infrastructure.security.OpportunityAuthorities;
import br.com.segsense.infrastructure.security.PublicationAuthorities;
import br.com.segsense.testsupport.MutableClock;
import com.jayway.jsonpath.JsonPath;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
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
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
@Testcontainers
@ActiveProfiles("test")
class OpportunityGovernanceIT {

  private static final Instant FIXED = Instant.parse("2026-09-04T12:00:00Z");

  @Container
  @ServiceConnection
  static PostgreSQLContainer postgres = new PostgreSQLContainer("postgres:18.6");

  @Autowired MockMvc mockMvc;
  @Autowired JdbcTemplate jdbcTemplate;
  @Autowired MutableClock clock;

  @TestConfiguration
  static class AdjustableClockConfig {
    @Bean
    @Primary
    MutableClock mutableClock() {
      return new MutableClock(FIXED);
    }
  }

  @Test
  void governsExactRevisionWithSegregationWindowsAndTrail() throws Exception {
    clock.setInstant(FIXED);
    String correlation = "88888888-8888-4888-8888-888888888888";
    Scope scope = seedActiveScope("gov-pub", "gov-ch", "gov-env");
    String base = opportunitiesUrl(scope);

    String created =
        mockMvc
            .perform(
                post(base)
                    .with(author())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(staticPayload("gov-crop", "Avaliar proteção agrícola")))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.status").value("DRAFT"))
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID opportunityId = UUID.fromString(JsonPath.read(created, "$.id"));
    long version = ((Number) JsonPath.read(created, "$.version")).longValue();
    String path = base + "/" + opportunityId;

    mockMvc
        .perform(
            post(path + "/governance/submit")
                .with(reader())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, 1, null)))
        .andExpect(status().isForbidden());

    mockMvc
        .perform(
            post(path + "/governance/submit")
                .with(author())
                .header("X-Correlation-ID", correlation)
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, null, null)))
        .andExpect(status().isOk())
        .andExpect(header().string("X-Correlation-ID", correlation))
        .andExpect(jsonPath("$.status").value("UNDER_REVIEW"))
        .andExpect(jsonPath("$.submittedRevision").value(1))
        .andExpect(jsonPath("$.publishedMeans").value("INTERNAL_AUTHORIZATION_ONLY"))
        .andExpect(jsonPath("$.availableActions").isArray());
    version++;
    tick();

    Integer eventCount =
        jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM segsense.opportunity_lifecycle_event WHERE opportunity_id = ? AND correlation_id = ?",
            Integer.class,
            opportunityId,
            UUID.fromString(correlation));
    assertThat(eventCount).isEqualTo(1);
    Integer decisionCountAfterSubmit =
        jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM segsense.opportunity_decision WHERE opportunity_id = ?",
            Integer.class,
            opportunityId);
    assertThat(decisionCountAfterSubmit).isZero();

    mockMvc
        .perform(
            post(path + "/governance/approve")
                .with(reviewer())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(0L, 1, null)))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.code").value("CONCURRENT_MODIFICATION"));
    assertThat(
            jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM segsense.opportunity_decision WHERE opportunity_id = ?",
                Integer.class,
                opportunityId))
        .isZero();
    assertThat(
            jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM segsense.opportunity_lifecycle_event WHERE opportunity_id = ?",
                Integer.class,
                opportunityId))
        .isEqualTo(1);

    mockMvc
        .perform(
            post(path + "/revisions")
                .with(author())
                .contentType(MediaType.APPLICATION_JSON)
                .content(revisionPayload(version, 1, "Nova revisão fora de rascunho")))
        .andExpect(status().isUnprocessableEntity())
        .andExpect(jsonPath("$.code").value("INVALID_GOVERNANCE_TRANSITION"));

    mockMvc
        .perform(
            post(path + "/governance/approve")
                .with(author())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, 1, null)))
        .andExpect(status().isForbidden())
        .andExpect(jsonPath("$.code").value("SEGREGATION_OF_DUTIES_VIOLATION"));

    mockMvc
        .perform(
            post(path + "/governance/approve")
                .with(reviewer())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, 9, null)))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.code").value("REVISION_NOT_CURRENT"));

    mockMvc
        .perform(
            post(path + "/governance/return-for-changes")
                .with(reviewer())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, 1, null)))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.code").value("JUSTIFICATION_REQUIRED"));

    mockMvc
        .perform(
            post(path + "/governance/return-for-changes")
                .with(reviewer())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, 1, "<script>ajuste</script>")))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));

    mockMvc
        .perform(
            post(path + "/governance/return-for-changes")
                .with(reviewer())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, 1, "Ajustar o resumo editorial.")))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("DRAFT"));
    version++;
    tick();

    mockMvc
        .perform(
            post(path + "/revisions")
                .with(author())
                .contentType(MediaType.APPLICATION_JSON)
                .content(revisionPayload(version, 1, "Revisão devolvida ajustada")))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.currentRevision").value(2));
    version++;

    mockMvc
        .perform(
            post(path + "/governance/submit")
                .with(author())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, null, null)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.submittedRevision").value(2));
    version++;
    tick();

    mockMvc
        .perform(
            post(path + "/governance/approve")
                .with(reviewer())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, 2, null)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("APPROVED"))
        .andExpect(jsonPath("$.approvedRevision").value(2));
    version++;
    tick();

    mockMvc
        .perform(
            post(path + "/publication/activate")
                .with(reviewer())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, null, null)))
        .andExpect(status().isForbidden())
        .andExpect(jsonPath("$.code").value("SEGREGATION_OF_DUTIES_VIOLATION"));

    mockMvc
        .perform(
            post(path + "/publication/activate")
                .with(activator())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, null, null)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("PUBLISHED"))
        .andExpect(jsonPath("$.effectivelyPublished").value(true))
        .andExpect(jsonPath("$.publishedMeans").value("INTERNAL_AUTHORIZATION_ONLY"));
    version++;
    tick();

    mockMvc
        .perform(
            post(path + "/publication/pause")
                .with(activator())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, null, null)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("PAUSED"));
    version++;
    tick();

    mockMvc
        .perform(
            post(path + "/publication/resume")
                .with(activator())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, null, null)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("PUBLISHED"));
    version++;
    tick();

    mockMvc
        .perform(
            post(path + "/publication/expire")
                .with(activator())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, null, null)))
        .andExpect(status().isUnprocessableEntity())
        .andExpect(jsonPath("$.code").value("PUBLICATION_NOT_EXPIRED"));

    mockMvc
        .perform(
            post(path + "/publication/pause")
                .with(activator())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(0L, null, null)))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.code").value("CONCURRENT_MODIFICATION"));
    Integer afterStale =
        jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM segsense.opportunity_lifecycle_event WHERE opportunity_id = ?",
            Integer.class,
            opportunityId);
    assertThat(afterStale).isEqualTo(7);
    assertThat(
            jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM segsense.opportunity_decision WHERE opportunity_id = ?",
                Integer.class,
                opportunityId))
        .isEqualTo(2);

    mockMvc
        .perform(get(path + "/governance/events").with(reader()).queryParam("page[size]", "3"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.items.length()").value(3))
        .andExpect(jsonPath("$.items[0].eventType").value("SUBMITTED"))
        .andExpect(jsonPath("$.page.next").isNotEmpty());

    MvcResult firstPage =
        mockMvc
            .perform(get(path + "/governance/events").with(reader()).queryParam("page[size]", "3"))
            .andReturn();
    String next = JsonPath.read(firstPage.getResponse().getContentAsString(), "$.page.next");
    mockMvc
        .perform(
            get(path + "/governance/events")
                .with(reader())
                .queryParam("page[size]", "3")
                .queryParam("page[after]", next))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.items[0].eventType").value("APPROVED"));

    Scope other = seedActiveScope("gov-other-pub", "gov-other-ch", "gov-other-env");
    mockMvc
        .perform(get(opportunitiesUrl(other) + "/" + opportunityId + "/governance").with(reader()))
        .andExpect(status().isNotFound());

    mockMvc
        .perform(
            post("/api/v1/admin/publishers/"
                    + scope.publisherId
                    + "/channels/"
                    + scope.channelId
                    + "/environments/"
                    + scope.environmentId
                    + "/status")
                .with(operator())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"SUSPENDED\",\"version\":" + scope.environmentVersion + "}"))
        .andExpect(status().isOk());

    mockMvc
        .perform(get(path + "/governance").with(reader()))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("PUBLISHED"))
        .andExpect(jsonPath("$.effectivelyPublished").value(false))
        .andExpect(jsonPath("$.effectivelyPublishable").value(false));
  }

  @Test
  void windowsAuthoritiesAnonymousAndSqlConstraints() throws Exception {
    clock.setInstant(FIXED);
    Scope scope = seedActiveScope("win-pub", "win-ch", "win-env");
    String base = opportunitiesUrl(scope);
    String futureBody =
        mockMvc
            .perform(
                post(base)
                    .with(author())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(
                        windowPayload(
                            "future-key",
                            "Janela futura de publicação",
                            "2026-09-04T13:00:00Z",
                            "2026-09-04T14:00:00Z")))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID futureId = UUID.fromString(JsonPath.read(futureBody, "$.id"));
    long futureVersion = ((Number) JsonPath.read(futureBody, "$.version")).longValue();
    String futurePath = base + "/" + futureId;
    futureVersion = submitAndApprove(futurePath, futureVersion, 1);
    mockMvc
        .perform(
            post(futurePath + "/publication/activate")
                .with(activator())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(futureVersion, null, null)))
        .andExpect(status().isUnprocessableEntity())
        .andExpect(jsonPath("$.code").value("PUBLICATION_WINDOW_NOT_OPEN"));

    String boundedBody =
        mockMvc
            .perform(
                post(base)
                    .with(author())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(
                        windowPayload(
                            "bounded-key",
                            "Janela limitada de publicação",
                            "2026-09-04T12:00:00Z",
                            "2026-09-04T12:30:00Z")))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID boundedId = UUID.fromString(JsonPath.read(boundedBody, "$.id"));
    long boundedVersion = ((Number) JsonPath.read(boundedBody, "$.version")).longValue();
    String boundedPath = base + "/" + boundedId;
    boundedVersion = submitAndApprove(boundedPath, boundedVersion, 1);
    mockMvc
        .perform(
            post(boundedPath + "/publication/activate")
                .with(activator())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(boundedVersion, null, null)))
        .andExpect(status().isOk());
    boundedVersion++;
    clock.setInstant(Instant.parse("2026-09-04T12:30:00Z"));
    mockMvc
        .perform(
            post(boundedPath + "/publication/expire")
                .with(activator())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(boundedVersion, null, null)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("EXPIRED"));
    clock.setInstant(FIXED);

    String correlation = "99999999-9999-4999-8999-999999999999";
    mockMvc
        .perform(get(futurePath + "/governance").header("X-Correlation-ID", correlation))
        .andExpect(status().isUnauthorized())
        .andExpect(header().string("X-Correlation-ID", correlation))
        .andExpect(jsonPath("$.code").value("AUTHENTICATION_REQUIRED"));

    mockMvc
        .perform(
            post(futurePath + "/governance/submit")
                .with(writerWithoutSubmit())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(0L, null, null)))
        .andExpect(status().isForbidden());
    mockMvc
        .perform(
            post(futurePath + "/publication/activate")
                .with(reader())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(0L, null, null)))
        .andExpect(status().isForbidden());

    mockMvc.perform(delete(futurePath + "/governance").with(author())).andExpect(status().isForbidden());
    mockMvc
        .perform(
            put(futurePath + "/publication/activate")
                .with(activator())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{}"))
        .andExpect(status().isForbidden());
    mockMvc
        .perform(
            patch(futurePath + "/governance")
                .with(author())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{}"))
        .andExpect(status().isForbidden());

    List<String> versions =
        jdbcTemplate.queryForList(
            "SELECT version FROM segsense.flyway_schema_history ORDER BY installed_rank",
            String.class);
    assertThat(versions).contains("1", "2", "3", "4", "5", "6");
  }

  @Test
  void sqlRejectsCrossIdentitiesAndKeepsFirstSubmissionImmutable() throws Exception {
    clock.setInstant(FIXED);
    Scope scope = seedActiveScope("int-pub", "int-ch", "int-env");
    String base = opportunitiesUrl(scope);

    List<String> versions =
        jdbcTemplate.queryForList(
            "SELECT version FROM segsense.flyway_schema_history ORDER BY installed_rank",
            String.class);
    assertThat(versions).contains("1", "2", "3", "4", "5", "6");
    assertThat(
            jdbcTemplate.queryForObject(
                """
                SELECT COUNT(*) FROM pg_constraint
                WHERE conname IN (
                  'opportunity_submission_identity_unique',
                  'opportunity_open_submission_identity_fk',
                  'opportunity_decision_submission_identity_fk')
                """,
                Integer.class))
        .isEqualTo(3);
    assertThat(
            jdbcTemplate.queryForObject(
                """
                SELECT COUNT(*) FROM pg_constraint
                WHERE conname IN (
                  'opportunity_open_submission_fk',
                  'opportunity_decision_submission_fk',
                  'opportunity_decision_revision_fk')
                """,
                Integer.class))
        .isZero();
    assertThat(
            jdbcTemplate.queryForObject(
                """
                SELECT COUNT(*) FROM pg_indexes
                WHERE schemaname = 'segsense'
                  AND indexname = 'opportunity_open_submission_unique'
                """,
                Integer.class))
        .isZero();

    UUID opportunityA = createSubmittedOpportunity(base, "int-a", "Oportunidade de integridade A");
    UUID opportunityB = createSubmittedOpportunity(base, "int-b", "Oportunidade de integridade B");
    UUID submissionA = openSubmissionId(opportunityA);
    UUID submissionB = openSubmissionId(opportunityB);

    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    "UPDATE segsense.contextual_opportunity SET open_submission_id = ? WHERE id = ?",
                    submissionB,
                    opportunityA))
        .isInstanceOf(org.springframework.dao.DataIntegrityViolationException.class);
    assertThat(openSubmissionId(opportunityA)).isEqualTo(submissionA);

    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    INSERT INTO segsense.opportunity_decision
                      (id, submission_id, opportunity_id, revision_number, outcome, decided_at, decided_by, correlation_id)
                    VALUES (?, ?, ?, 1, 'APPROVED', NOW(), 'reviewer', ?)
                    """,
                    UUID.randomUUID(),
                    submissionA,
                    opportunityB,
                    UUID.randomUUID()))
        .isInstanceOf(org.springframework.dao.DataIntegrityViolationException.class);

    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    INSERT INTO segsense.opportunity_decision
                      (id, submission_id, opportunity_id, revision_number, outcome, decided_at, decided_by, correlation_id)
                    VALUES (?, ?, ?, 2, 'APPROVED', NOW(), 'reviewer', ?)
                    """,
                    UUID.randomUUID(),
                    submissionA,
                    opportunityA,
                    UUID.randomUUID()))
        .isInstanceOf(org.springframework.dao.DataIntegrityViolationException.class);

    UUID coherentDecision = UUID.randomUUID();
    jdbcTemplate.update(
        """
        INSERT INTO segsense.opportunity_decision
          (id, submission_id, opportunity_id, revision_number, outcome, decided_at, decided_by, correlation_id)
        VALUES (?, ?, ?, 1, 'APPROVED', NOW(), 'reviewer', ?)
        """,
        coherentDecision,
        submissionA,
        opportunityA,
        UUID.randomUUID());
    assertThat(
            jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM segsense.opportunity_decision WHERE id = ?",
                Integer.class,
                coherentDecision))
        .isEqualTo(1);

    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    INSERT INTO segsense.opportunity_decision
                      (id, submission_id, opportunity_id, revision_number, outcome, decided_at, decided_by, correlation_id)
                    VALUES (?, ?, ?, 1, 'APPROVED', NOW(), 'reviewer', ?)
                    """,
                    UUID.randomUUID(),
                    submissionA,
                    opportunityA,
                    UUID.randomUUID()))
        .isInstanceOf(org.springframework.dao.DataIntegrityViolationException.class);

    String created =
        mockMvc
            .perform(
                post(base)
                    .with(author())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(staticPayload("int-resub", "Ressubmissão imutável")))
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
                .content(command(version, null, null)))
        .andExpect(status().isOk());
    version++;
    UUID firstSubmissionId = openSubmissionId(opportunityId);
    Map<String, Object> firstSnapshot = submissionIdentity(firstSubmissionId);

    mockMvc
        .perform(
            post(path + "/governance/return-for-changes")
                .with(reviewer())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, 1, "Ajustar o resumo editorial.")))
        .andExpect(status().isOk());
    version++;
    assertThat(submissionIdentity(firstSubmissionId)).isEqualTo(firstSnapshot);
    assertThat(openSubmissionIdOrNull(opportunityId)).isNull();

    mockMvc
        .perform(
            post(path + "/revisions")
                .with(author())
                .contentType(MediaType.APPLICATION_JSON)
                .content(revisionPayload(version, 1, "Revisão devolvida ajustada")))
        .andExpect(status().isOk());
    version++;
    mockMvc
        .perform(
            post(path + "/governance/submit")
                .with(author())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, null, null)))
        .andExpect(status().isOk());
    UUID secondSubmissionId = openSubmissionId(opportunityId);
    assertThat(secondSubmissionId).isNotEqualTo(firstSubmissionId);
    assertThat(submissionIdentity(firstSubmissionId)).isEqualTo(firstSnapshot);
    assertThat(
            jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM segsense.opportunity_submission WHERE opportunity_id = ?",
                Integer.class,
                opportunityId))
        .isEqualTo(2);
    assertThat(
            jdbcTemplate.queryForObject(
                "SELECT status FROM segsense.opportunity_submission WHERE id = ?",
                String.class,
                firstSubmissionId))
        .isEqualTo("OPEN");
  }

  @Test
  void rejectProducesRevokedWithoutReuse() throws Exception {
    clock.setInstant(FIXED);
    Scope scope = seedActiveScope("rej-pub", "rej-ch", "rej-env");
    String created =
        mockMvc
            .perform(
                post(opportunitiesUrl(scope))
                    .with(author())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(staticPayload("rej-crop", "Avaliar proteção agrícola")))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID opportunityId = UUID.fromString(JsonPath.read(created, "$.id"));
    long version = ((Number) JsonPath.read(created, "$.version")).longValue();
    String path = opportunitiesUrl(scope) + "/" + opportunityId;
    mockMvc
        .perform(
            post(path + "/governance/submit")
                .with(author())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, null, null)))
        .andExpect(status().isOk());
    version++;
    mockMvc
        .perform(
            post(path + "/governance/reject")
                .with(reviewer())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, 1, "Conteúdo editorial insuficiente.")))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("REVOKED"));
    version++;
    mockMvc
        .perform(
            post(path + "/governance/submit")
                .with(author())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, null, null)))
        .andExpect(status().isUnprocessableEntity())
        .andExpect(jsonPath("$.code").value("INVALID_GOVERNANCE_TRANSITION"));
  }

  private void tick() {
    clock.setInstant(clock.instant().plusSeconds(1));
  }

  private UUID createSubmittedOpportunity(String base, String key, String title) throws Exception {
    String created =
        mockMvc
            .perform(
                post(base)
                    .with(author())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(staticPayload(key, title)))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID opportunityId = UUID.fromString(JsonPath.read(created, "$.id"));
    long version = ((Number) JsonPath.read(created, "$.version")).longValue();
    mockMvc
        .perform(
            post(base + "/" + opportunityId + "/governance/submit")
                .with(author())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, null, null)))
        .andExpect(status().isOk());
    return opportunityId;
  }

  private UUID openSubmissionId(UUID opportunityId) {
    UUID submissionId = openSubmissionIdOrNull(opportunityId);
    assertThat(submissionId).isNotNull();
    return submissionId;
  }

  private UUID openSubmissionIdOrNull(UUID opportunityId) {
    return jdbcTemplate.queryForObject(
        "SELECT open_submission_id FROM segsense.contextual_opportunity WHERE id = ?",
        UUID.class,
        opportunityId);
  }

  private Map<String, Object> submissionIdentity(UUID submissionId) {
    return jdbcTemplate.queryForMap(
        """
        SELECT id, opportunity_id, revision_number, submitted_at, submitted_by,
               correlation_id, status, xmin::text AS tuple_xmin, ctid::text AS tuple_ctid
        FROM segsense.opportunity_submission
        WHERE id = ?
        """,
        submissionId);
  }

  private long submitAndApprove(String path, long version, int revision) throws Exception {
    mockMvc
        .perform(
            post(path + "/governance/submit")
                .with(author())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, null, null)))
        .andExpect(status().isOk());
    version++;
    mockMvc
        .perform(
            post(path + "/governance/approve")
                .with(reviewer())
                .contentType(MediaType.APPLICATION_JSON)
                .content(command(version, revision, null)))
        .andExpect(status().isOk());
    return version + 1;
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
                        "{\"key\":\""
                            + channelKey
                            + "\",\"name\":\"Canal "
                            + channelKey
                            + "\",\"type\":\"WEBSITE\"}"))
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
    String activated =
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
            .andExpect(status().isOk())
            .andReturn()
            .getResponse()
            .getContentAsString();
    return new Scope(
        publisherId,
        channelId,
        environmentId,
        ((Number) JsonPath.read(activated, "$.version")).longValue());
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

  private static String staticPayload(String key, String title) {
    return """
        {"key":"%s","title":"%s","contextMode":"STATIC",
         "contextSummaryTemplate":"Resumo estático de contexto.",
         "objectiveTemplate":"Objetivo estático de avaliação.","callToActionLabel":"Avaliar"}
        """
        .formatted(key, title);
  }

  private static String windowPayload(String key, String title, String from, String until) {
    return """
        {"key":"%s","title":"%s","contextMode":"STATIC",
         "contextSummaryTemplate":"Resumo estático de contexto.",
         "objectiveTemplate":"Objetivo estático de avaliação.","callToActionLabel":"Avaliar",
         "validFrom":"%s","validUntil":"%s"}
        """
        .formatted(key, title, from, until);
  }

  private static String revisionPayload(long expectedVersion, int baseRevision, String title) {
    return """
        {"expectedVersion":%s,"baseRevision":%s,"title":"%s","contextMode":"STATIC",
         "contextSummaryTemplate":"Resumo estático de contexto.",
         "objectiveTemplate":"Objetivo estático de avaliação.","callToActionLabel":"Avaliar"}
        """
        .formatted(expectedVersion, baseRevision, title);
  }

  private static String command(long expectedVersion, Integer revisionNumber, String justification) {
    StringBuilder json = new StringBuilder("{\"expectedVersion\":").append(expectedVersion);
    if (revisionNumber != null) {
      json.append(",\"revisionNumber\":").append(revisionNumber);
    }
    if (justification != null) {
      json.append(",\"justification\":").append(toJsonString(justification));
    }
    return json.append('}').toString();
  }

  private static String toJsonString(String value) {
    return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
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
            new SimpleGrantedAuthority(OpportunityAuthorities.SUBMIT),
            new SimpleGrantedAuthority(OpportunityAuthorities.REVIEW));
  }

  private static RequestPostProcessor reviewer() {
    return user("reviewer")
        .authorities(
            new SimpleGrantedAuthority(OpportunityAuthorities.READ),
            new SimpleGrantedAuthority(OpportunityAuthorities.REVIEW),
            new SimpleGrantedAuthority(PublicationAuthorities.MANAGE));
  }

  private static RequestPostProcessor activator() {
    return user("activator")
        .authorities(
            new SimpleGrantedAuthority(OpportunityAuthorities.READ),
            new SimpleGrantedAuthority(PublicationAuthorities.MANAGE));
  }

  private static RequestPostProcessor reader() {
    return user("reader")
        .authorities(new SimpleGrantedAuthority(OpportunityAuthorities.READ));
  }

  private static RequestPostProcessor writerWithoutSubmit() {
    return user("writer-only")
        .authorities(
            new SimpleGrantedAuthority(OpportunityAuthorities.READ),
            new SimpleGrantedAuthority(OpportunityAuthorities.WRITE));
  }

  private record Scope(
      UUID publisherId, UUID channelId, UUID environmentId, long environmentVersion) {}
}
