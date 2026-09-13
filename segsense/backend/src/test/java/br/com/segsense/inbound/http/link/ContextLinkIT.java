package br.com.segsense.inbound.http.link;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import br.com.segsense.application.link.OpaqueTokenGenerator;
import br.com.segsense.infrastructure.security.CatalogAuthorities;
import br.com.segsense.infrastructure.security.LinkAuthorities;
import br.com.segsense.infrastructure.security.OpportunityAuthorities;
import br.com.segsense.infrastructure.security.PublicationAuthorities;
import br.com.segsense.testsupport.MutableClock;
import com.jayway.jsonpath.JsonPath;
import java.time.Instant;
import java.util.List;
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
import org.springframework.dao.DataIntegrityViolationException;
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
class ContextLinkIT {

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
          String seed = "tok" + sequence.incrementAndGet() + "x".repeat(43);
          return seed.substring(0, 43);
        };
    }
  }

  @Test
  void issuesResolvesRevokesAndProtectsPublicEnvelope() throws Exception {
    clock.setInstant(FIXED);
    Scope scope = seedActiveScope("lnk-pub", "lnk-ch", "lnk-env");
    String base = opportunitiesUrl(scope);
    Published published = publishDynamic(scope, "crop-risk", base);

    mockMvc
        .perform(
            post(published.links)
                .with(reader())
                .contentType(MediaType.APPLICATION_JSON)
                .content(issuePayload("artigo-quebra-safra-2026", "2026-10-01T00:00:00Z")))
        .andExpect(status().isForbidden());

    mockMvc
        .perform(post(published.links).contentType(MediaType.APPLICATION_JSON).content("{}"))
        .andExpect(status().isUnauthorized());

    String issuedBody =
        mockMvc
            .perform(
                post(published.links)
                    .with(manager())
                    .header("Host", "evil.example")
                    .header("X-Forwarded-Host", "evil.example")
                    .header("X-Forwarded-Proto", "https")
                    .header("X-Correlation-ID", "99999999-9999-4999-8999-999999999999")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(issuePayload("artigo-quebra-safra-2026", "2026-10-01T00:00:00Z")))
            .andExpect(status().isCreated())
            .andExpect(header().string("Cache-Control", "no-store"))
            .andExpect(header().string("Pragma", "no-cache"))
            .andExpect(header().string("Referrer-Policy", "no-referrer"))
            .andExpect(header().string("X-Content-Type-Options", "nosniff"))
            .andExpect(jsonPath("$.token").isString())
            .andExpect(jsonPath("$.publicUrl").value(org.hamcrest.Matchers.startsWith("http://127.0.0.1:5178/c/")))
            .andExpect(jsonPath("$.id").exists())
            .andExpect(jsonPath("$.publisherContext[*].fieldKey", org.hamcrest.Matchers.hasItems("riskType", "area")))
            .andReturn()
            .getResponse()
            .getContentAsString();
    String tokenOne = JsonPath.read(issuedBody, "$.token");
    assertThat(tokenOne).hasSize(43);
    assertThat((String) JsonPath.read(issuedBody, "$.publicUrl"))
        .isEqualTo("http://127.0.0.1:5178/c/" + tokenOne);

    String list =
        mockMvc
            .perform(get(published.links).with(manager()))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.items[0].token").doesNotExist())
            .andExpect(jsonPath("$.items[0].publicUrl").doesNotExist())
            .andExpect(jsonPath("$.items[0].effectiveStatus").value("ACTIVE"))
            .andReturn()
            .getResponse()
            .getContentAsString();
    String linkId = JsonPath.read(list, "$.items[0].id");

    mockMvc
        .perform(
            post(published.links)
                .with(manager())
                .contentType(MediaType.APPLICATION_JSON)
                .content(issuePayload("artigo-quebra-safra-2026", "2026-10-01T00:00:00Z")))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.code").value("LINK_PLACEMENT_CONFLICT"));

    String second =
        mockMvc
            .perform(
                post(published.links)
                    .with(manager())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(issuePayload("artigo-quebra-safra-b", "2026-10-01T00:00:00Z")))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.token").isString())
            .andReturn()
            .getResponse()
            .getContentAsString();
    String tokenTwo = JsonPath.read(second, "$.token");
    assertThat(tokenTwo).isNotEqualTo(tokenOne);

    Integer digestCount =
        jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM segsense.published_context_link WHERE octet_length(token_digest) = 32",
            Integer.class);
    assertThat(digestCount).isEqualTo(2);
    Integer rawHintFullToken =
        jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM segsense.published_context_link WHERE token_hint = ?",
            Integer.class,
            tokenOne);
    assertThat(rawHintFullToken).isZero();

    mockMvc
        .perform(get("/api/v1/public/context-links/" + tokenOne))
        .andExpect(status().isOk())
        .andExpect(header().string("Cache-Control", "no-store"))
        .andExpect(header().string("Referrer-Policy", "no-referrer"))
        .andExpect(jsonPath("$.applicationId").value("SEGSENSE"))
        .andExpect(jsonPath("$.title").exists())
        .andExpect(jsonPath("$.objectiveTemplate").doesNotExist())
        .andExpect(jsonPath("$.opportunityId").doesNotExist())
        .andExpect(jsonPath("$.publisherId").doesNotExist())
        .andExpect(jsonPath("$.token").doesNotExist())
        .andExpect(jsonPath("$.tokenHint").doesNotExist())
        .andExpect(jsonPath("$.quotationPerformed").value(false))
        .andExpect(jsonPath("$.eligibilityEvaluated").value(false))
        .andExpect(jsonPath("$.recommendationPerformed").value(false))
        .andExpect(jsonPath("$.publisherBindings[*].value", org.hamcrest.Matchers.hasItem("quebra-safra")))
        .andExpect(jsonPath("$.userFields[0].key").value("comment"));

    Integer eventCountBefore =
        jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM segsense.published_context_link_event", Integer.class);

    mockMvc
        .perform(get("/api/v1/public/context-links/short"))
        .andExpect(status().isNotFound())
        .andExpect(jsonPath("$.code").value("CONTEXT_LINK_NOT_FOUND"));
    mockMvc
        .perform(get("/api/v1/public/context-links/" + "C".repeat(43)))
        .andExpect(status().isNotFound())
        .andExpect(jsonPath("$.code").value("CONTEXT_LINK_NOT_FOUND"));

    Integer eventCountAfter =
        jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM segsense.published_context_link_event", Integer.class);
    assertThat(eventCountAfter).isEqualTo(eventCountBefore);

    mockMvc
        .perform(
            post(published.links + "/" + linkId + "/revoke")
                .with(manager())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"expectedVersion\":0,\"justification\":\"Revogacao administrativa do artigo.\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("REVOKED"));

    mockMvc
        .perform(get("/api/v1/public/context-links/" + tokenOne))
        .andExpect(status().isGone())
        .andExpect(jsonPath("$.code").value("CONTEXT_LINK_REVOKED"));

    mockMvc
        .perform(
            post(published.path + "/publication/pause")
                .with(activator())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"expectedVersion\":" + published.version + "}"))
        .andExpect(status().isOk());

    mockMvc
        .perform(get("/api/v1/public/context-links/" + tokenTwo))
        .andExpect(status().isServiceUnavailable())
        .andExpect(header().string("Retry-After", "60"))
        .andExpect(jsonPath("$.code").value("CONTEXT_LINK_TEMPORARILY_UNAVAILABLE"));

    mockMvc
        .perform(
            post(published.path + "/publication/resume")
                .with(activator())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"expectedVersion\":" + (published.version + 1) + "}"))
        .andExpect(status().isOk());

    mockMvc
        .perform(get("/api/v1/public/context-links/" + tokenOne))
        .andExpect(status().isGone())
        .andExpect(jsonPath("$.code").value("CONTEXT_LINK_REVOKED"));

    mockMvc.perform(put(published.links).with(manager())).andExpect(status().isForbidden());
    mockMvc.perform(patch(published.links + "/" + linkId).with(manager())).andExpect(status().isForbidden());
    mockMvc.perform(delete(published.links + "/" + linkId).with(manager())).andExpect(status().isForbidden());

    mockMvc
        .perform(
            options("/api/v1/public/context-links/" + tokenTwo)
                .header("Origin", "http://evil.example")
                .header("Access-Control-Request-Method", "GET"))
        .andExpect(header().doesNotExist("Access-Control-Allow-Origin"));

    List<String> versions =
        jdbcTemplate.queryForList(
            "SELECT version FROM segsense.flyway_schema_history ORDER BY installed_rank",
            String.class);
    assertThat(versions).contains("1", "2", "3", "4", "5", "6", "7", "8");

    Integer placementUnique =
        jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM pg_constraint WHERE conname = 'published_context_link_placement_unique'",
            Integer.class);
    assertThat(placementUnique).isEqualTo(1);
    Integer digestUnique =
        jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM pg_constraint WHERE conname = 'published_context_link_digest_unique'",
            Integer.class);
    assertThat(digestUnique).isEqualTo(1);
    Integer approvedUnique =
        jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM pg_constraint WHERE conname = 'opportunity_id_approved_revision_unique'",
            Integer.class);
    assertThat(approvedUnique).isEqualTo(1);
    Integer approvedFk =
        jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM pg_constraint WHERE conname = 'published_context_link_approved_revision_fk'",
            Integer.class);
    assertThat(approvedFk).isEqualTo(1);
    Integer bindingFieldFk =
        jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM pg_constraint WHERE conname = 'published_context_link_binding_field_fk'",
            Integer.class);
    assertThat(bindingFieldFk).isEqualTo(1);
  }

  @Test
  void rejectsIssueOutsidePublishedWindowAndInvalidBindings() throws Exception {
    clock.setInstant(FIXED);
    Scope scope = seedActiveScope("lnk2-pub", "lnk2-ch", "lnk2-env");
    String base = opportunitiesUrl(scope);
    String created =
        mockMvc
            .perform(
                post(base)
                    .with(author())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(dynamicPayload("draft-crop")))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID opportunityId = UUID.fromString(JsonPath.read(created, "$.id"));
    String links = base + "/" + opportunityId + "/links";
    mockMvc
        .perform(
            post(links)
                .with(manager())
                .contentType(MediaType.APPLICATION_JSON)
                .content(issuePayload("artigo-quebra-safra-x", "2026-10-01T00:00:00Z")))
        .andExpect(status().isUnprocessableEntity())
        .andExpect(jsonPath("$.code").value("OPPORTUNITY_NOT_PUBLISHED"));

    Published published = publishDynamic(scope, "live-crop", base);
    mockMvc
        .perform(
            post(published.links)
                .with(manager())
                .contentType(MediaType.APPLICATION_JSON)
                .content(issuePayload("artigo-expiracao-longa", "2026-12-01T00:00:00Z")))
        .andExpect(status().isUnprocessableEntity())
        .andExpect(jsonPath("$.code").value("LINK_EXPIRY_INVALID"));

    mockMvc
        .perform(
            post(published.links)
                .with(manager())
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    """
                    {"placementKey":"artigo-coercao","label":"Artigo coercao xx","expiresAt":"2026-10-01T00:00:00Z",
                     "publisherContext":[{"fieldKey":"area","value":"12.5"}]}
                    """))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.code").value("INVALID_PUBLISHER_CONTEXT"));

    mockMvc
        .perform(
            post(published.links)
                .with(manager())
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    """
                    {"placementKey":"artigo-user","label":"Artigo usuario xx","expiresAt":"2026-10-01T00:00:00Z",
                     "publisherContext":[{"fieldKey":"comment","value":"texto"}]}
                    """))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.code").value("INVALID_PUBLISHER_CONTEXT"));
  }

  @Test
  void expiredLinkIsGoneAndCrossScopeIsNotFound() throws Exception {
    clock.setInstant(FIXED);
    Scope scope = seedActiveScope("lnk3-pub", "lnk3-ch", "lnk3-env");
    Published published = publishDynamic(scope, "exp-crop", opportunitiesUrl(scope));
    String issued =
        mockMvc
            .perform(
                post(published.links)
                    .with(manager())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(issuePayload("artigo-expira", "2026-09-05T12:00:00Z")))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();
    String token = JsonPath.read(issued, "$.token");
    clock.setInstant(Instant.parse("2026-09-05T12:00:00Z"));
    mockMvc
        .perform(get("/api/v1/public/context-links/" + token))
        .andExpect(status().isGone())
        .andExpect(jsonPath("$.code").value("CONTEXT_LINK_EXPIRED"));

    Scope other = seedActiveScope("lnk-other-pub", "lnk-other-ch", "lnk-other-env");
    mockMvc
        .perform(
            get(opportunitiesUrl(other) + "/" + published.opportunityId + "/links")
                .with(manager()))
        .andExpect(status().isNotFound());
  }

  @Test
  void sqlRejectsLinkToExistingButUnapprovedRevisionAndUnknownBinding() throws Exception {
    clock.setInstant(FIXED);
    Scope scope = seedActiveScope("lnk8-pub", "lnk8-ch", "lnk8-env");
    Published published = publishDynamic(scope, "live-v8", opportunitiesUrl(scope));

    UUID approvedRevisionId =
        jdbcTemplate.queryForObject(
            """
            SELECT r.id
            FROM segsense.contextual_opportunity_revision r
            JOIN segsense.contextual_opportunity o ON o.id = r.opportunity_id
            WHERE o.id = ? AND r.revision_number = o.approved_revision
            """,
            UUID.class,
            published.opportunityId);
    String approvedDef =
        jdbcTemplate.queryForObject(
            """
            SELECT pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conname = 'published_context_link_approved_revision_fk'
            """,
            String.class);
    assertThat(approvedDef)
        .contains("opportunity_id")
        .contains("revision_number")
        .contains("approved_revision");

    UUID extraRevisionId = UUID.randomUUID();
    jdbcTemplate.update(
        """
        INSERT INTO segsense.contextual_opportunity_revision (
          id, opportunity_id, revision_number, title, context_mode,
          context_summary_template, objective_template, call_to_action_label,
          valid_from, valid_until, created_at, created_by)
        SELECT ?, opportunity_id, 2, title, context_mode,
               context_summary_template, objective_template, call_to_action_label,
               valid_from, valid_until, created_at, created_by
        FROM segsense.contextual_opportunity_revision
        WHERE opportunity_id = ? AND revision_number = 1
        """,
        extraRevisionId,
        published.opportunityId);

    UUID approvedLinkId = UUID.randomUUID();
    insertDirectLink(
        approvedLinkId,
        scope,
        published.opportunityId,
        1,
        approvedRevisionId,
        "artigo-aprovado-v8",
        digest(1));

    assertThatThrownBy(
            () ->
                insertDirectLink(
                    UUID.randomUUID(),
                    scope,
                    published.opportunityId,
                    2,
                    extraRevisionId,
                    "artigo-historico-v8",
                    digest(2)))
        .isInstanceOf(DataIntegrityViolationException.class);

    UUID foreignPublisher = UUID.randomUUID();
    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    INSERT INTO segsense.published_context_link (
                      id, publisher_id, channel_id, environment_id, opportunity_id,
                      revision_number, opportunity_revision_id, placement_key, label,
                      token_digest, token_hint, status, issued_at, issued_by, expires_at,
                      version, issued_correlation_id)
                    VALUES (?, ?, ?, ?, ?, 1, ?, 'artigo-escopo-v8', 'Artigo escopo v8x',
                            ?, 'xxxxxxxx', 'ACTIVE', TIMESTAMPTZ '2026-09-04T12:00:00Z', 'it',
                            TIMESTAMPTZ '2026-10-01T00:00:00Z', 0, ?)
                    """,
                    UUID.randomUUID(),
                    foreignPublisher,
                    scope.channelId,
                    scope.environmentId,
                    published.opportunityId,
                    approvedRevisionId,
                    digest(3),
                    UUID.randomUUID()))
        .isInstanceOf(DataIntegrityViolationException.class);

    UUID bindingId = UUID.randomUUID();
    jdbcTemplate.update(
        """
        INSERT INTO segsense.published_context_link_binding (
          id, link_id, opportunity_revision_id, field_key, field_type, field_source, text_value)
        VALUES (?, ?, ?, 'riskType', 'ENUM', 'PUBLISHER', 'quebra-safra')
        """,
        bindingId,
        approvedLinkId,
        approvedRevisionId);

    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    INSERT INTO segsense.published_context_link_binding (
                      id, link_id, opportunity_revision_id, field_key, field_type, field_source, text_value)
                    VALUES (?, ?, ?, 'unknownKey', 'TEXT', 'PUBLISHER', 'nope')
                    """,
                    UUID.randomUUID(),
                    approvedLinkId,
                    approvedRevisionId))
        .isInstanceOf(DataIntegrityViolationException.class);

    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    INSERT INTO segsense.published_context_link_binding (
                      id, link_id, opportunity_revision_id, field_key, field_type, field_source, text_value)
                    VALUES (?, ?, ?, 'riskType', 'TEXT', 'PUBLISHER', 'quebra-safra')
                    """,
                    UUID.randomUUID(),
                    approvedLinkId,
                    approvedRevisionId))
        .isInstanceOf(DataIntegrityViolationException.class);

    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    INSERT INTO segsense.published_context_link_binding (
                      id, link_id, opportunity_revision_id, field_key, field_type, field_source, text_value)
                    VALUES (?, ?, ?, 'comment', 'TEXT', 'USER', 'comentario')
                    """,
                    UUID.randomUUID(),
                    approvedLinkId,
                    approvedRevisionId))
        .isInstanceOf(DataIntegrityViolationException.class);
  }

  private void insertDirectLink(
      UUID linkId,
      Scope scope,
      UUID opportunityId,
      int revisionNumber,
      UUID opportunityRevisionId,
      String placementKey,
      byte[] digest) {
    jdbcTemplate.update(
        """
        INSERT INTO segsense.published_context_link (
          id, publisher_id, channel_id, environment_id, opportunity_id,
          revision_number, opportunity_revision_id, placement_key, label,
          token_digest, token_hint, status, issued_at, issued_by, expires_at,
          version, issued_correlation_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Artigo aprovado v8x',
                ?, 'xxxxxxxx', 'ACTIVE', TIMESTAMPTZ '2026-09-04T12:00:00Z', 'it',
                TIMESTAMPTZ '2026-10-01T00:00:00Z', 0, ?)
        """,
        linkId,
        scope.publisherId,
        scope.channelId,
        scope.environmentId,
        opportunityId,
        revisionNumber,
        opportunityRevisionId,
        placementKey,
        digest,
        UUID.randomUUID());
  }

  private static byte[] digest(int seed) {
    byte[] digest = new byte[32];
    digest[0] = (byte) seed;
    digest[31] = (byte) (seed + 7);
    return digest;
  }

  private Published publishDynamic(Scope scope, String key, String base) throws Exception {
    String created =
        mockMvc
            .perform(
                post(base)
                    .with(author())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(dynamicPayload(key)))
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

  private static RequestPostProcessor reader() {
    return user("link-reader").authorities(new SimpleGrantedAuthority(LinkAuthorities.READ));
  }

  private record Scope(UUID publisherId, UUID channelId, UUID environmentId) {}

  private record Published(UUID opportunityId, String path, String links, long version) {}
}
