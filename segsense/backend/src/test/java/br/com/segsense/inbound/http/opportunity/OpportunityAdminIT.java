package br.com.segsense.inbound.http.opportunity;

import static org.assertj.core.api.Assertions.assertThat;
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
import com.jayway.jsonpath.JsonPath;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
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
class OpportunityAdminIT {

  @Container
  @ServiceConnection
  static PostgreSQLContainer postgres = new PostgreSQLContainer("postgres:18.6");

  @Autowired MockMvc mockMvc;
  @Autowired JdbcTemplate jdbcTemplate;

  @Test
  void createsImmutableRevisionsValidatesAndScopesAvailability() throws Exception {
    String correlation = "66666666-6666-4666-8666-666666666666";
    Scope scope = seedActiveScope("opp-pub", "opp-ch", "opp-env");
    String base = opportunitiesUrl(scope);

    String createdBody =
        mockMvc
            .perform(
                post(base)
                    .with(opportunityWriter())
                    .header("X-Correlation-ID", correlation)
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(staticPayload("crop-risk", "Avaliar proteção agrícola")))
            .andExpect(status().isCreated())
            .andExpect(header().string("X-Correlation-ID", correlation))
            .andExpect(jsonPath("$.key").value("crop-risk"))
            .andExpect(jsonPath("$.status").value("DRAFT"))
            .andExpect(jsonPath("$.currentRevision").value(1))
            .andExpect(jsonPath("$.effectivelyAvailable").value(true))
            .andExpect(jsonPath("$.current.contextMode").value("STATIC"))
            .andExpect(jsonPath("$.current.contextFields.length()").value(0))
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID opportunityId = UUID.fromString(JsonPath.read(createdBody, "$.id"));
    long version = ((Number) JsonPath.read(createdBody, "$.version")).longValue();

    mockMvc
        .perform(
            post(base)
                .with(opportunityWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content(staticPayload("crop-risk", "Outro título válido xx")))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.code").value("OPPORTUNITY_KEY_CONFLICT"));

    mockMvc
        .perform(
            post(base)
                .with(opportunityWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    """
                    {"key":"html-bad","title":"<script>x</script>abc","contextMode":"STATIC",
                     "contextSummaryTemplate":"Resumo estático de contexto.",
                     "objectiveTemplate":"Objetivo estático de avaliação.","callToActionLabel":"Avaliar"}
                    """))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));

    mockMvc
        .perform(
            post(base)
                .with(opportunityWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content(dynamicPayload("crop-dyn", true)))
        .andExpect(status().isCreated())
        .andExpect(jsonPath("$.current.contextMode").value("DYNAMIC"))
        .andExpect(jsonPath("$.current.contextFields[0].key").value("cropType"));

    mockMvc
        .perform(get(base).with(opportunityWriter()).queryParam("page[size]", "1"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.items.length()").value(1))
        .andExpect(jsonPath("$.page.next").isNotEmpty());

    mockMvc
        .perform(
            post(base)
                .with(opportunityWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content(dynamicPayload("crop-pii", false)))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));

    String revisionUrl = base + "/" + opportunityId + "/revisions";
    String sameContent =
        mockMvc
            .perform(
                post(revisionUrl)
                    .with(opportunityWriter())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(revisionPayload(version, 1, "Avaliar proteção agrícola", "STATIC", null)))
            .andExpect(status().isUnprocessableEntity())
            .andExpect(jsonPath("$.code").value("NO_CONTENT_CHANGE"))
            .andReturn()
            .getResponse()
            .getContentAsString();
    assertThat(sameContent).doesNotContain("SQL", "duplicate key", "ERROR:", "org.postgresql");

    mockMvc
        .perform(
            post(revisionUrl)
                .with(opportunityWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content(revisionPayload(version, 0, "Avaliar outra proteção xx", "STATIC", null)))
        .andExpect(status().isBadRequest());

    mockMvc
        .perform(
            post(revisionUrl)
                .with(opportunityWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content(revisionPayload(version, 1, "Avaliar outra proteção xx", "STATIC", null)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.currentRevision").value(2))
        .andExpect(jsonPath("$.status").value("DRAFT"))
        .andExpect(jsonPath("$.current.title").value("Avaliar outra proteção xx"));

    mockMvc
        .perform(get(base + "/" + opportunityId + "/revisions/1").with(opportunityWriter()))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.revisionNumber").value(1))
        .andExpect(jsonPath("$.title").value("Avaliar proteção agrícola"));

    Integer historicTitleCount =
        jdbcTemplate.queryForObject(
            """
            SELECT COUNT(*) FROM segsense.contextual_opportunity_revision
            WHERE opportunity_id = ? AND revision_number = 1 AND title = 'Avaliar proteção agrícola'
            """,
            Integer.class,
            opportunityId);
    assertThat(historicTitleCount).isEqualTo(1);

    mockMvc
        .perform(
            post(revisionUrl)
                .with(opportunityWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content(revisionPayload(version, 2, "Terceira revisão válida", "STATIC", null)))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.code").value("CONCURRENT_MODIFICATION"));

    mockMvc
        .perform(
            post(revisionUrl)
                .with(opportunityWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content(revisionPayload(version + 1, 1, "Terceira revisão válida", "STATIC", null)))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.code").value("STALE_OPPORTUNITY_REVISION"));

    mockMvc
        .perform(get(base + "/" + opportunityId).with(opportunityWriter()))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.currentRevision").value(2));

    MvcResult history =
        mockMvc
            .perform(
                get(revisionUrl).with(opportunityWriter()).queryParam("page[size]", "1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.items.length()").value(1))
            .andExpect(jsonPath("$.items[0].revisionNumber").value(1))
            .andExpect(jsonPath("$.page.next").isNotEmpty())
            .andReturn();
    String next = JsonPath.read(history.getResponse().getContentAsString(), "$.page.next");
    mockMvc
        .perform(
            get(revisionUrl)
                .with(opportunityWriter())
                .queryParam("page[size]", "1")
                .queryParam("page[after]", next))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.items[0].revisionNumber").value(2));

    String tampered =
        java.util.Base64.getUrlEncoder()
            .withoutPadding()
            .encodeToString((UUID.randomUUID() + "|1").getBytes(java.nio.charset.StandardCharsets.UTF_8));
    mockMvc
        .perform(
            get(revisionUrl)
                .with(opportunityWriter())
                .queryParam("page[size]", "1")
                .queryParam("page[after]", tampered))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));

    Scope other = seedActiveScope("other-pub", "other-ch", "other-env");
    mockMvc
        .perform(get(opportunitiesUrl(other) + "/" + opportunityId).with(opportunityWriter()))
        .andExpect(status().isNotFound())
        .andExpect(jsonPath("$.code").value("NOT_FOUND"));

    mockMvc
        .perform(
            post("/api/v1/admin/publishers/"
                    + scope.publisherId
                    + "/channels/"
                    + scope.channelId
                    + "/environments/"
                    + scope.environmentId
                    + "/status")
                .with(opportunityWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"SUSPENDED\",\"version\":" + scope.environmentVersion + "}"))
        .andExpect(status().isOk());

    mockMvc
        .perform(get(base + "/" + opportunityId).with(opportunityWriter()))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("DRAFT"))
        .andExpect(jsonPath("$.effectivelyAvailable").value(false));

    mockMvc
        .perform(delete(base + "/" + opportunityId).with(opportunityWriter()))
        .andExpect(status().isForbidden());
    mockMvc
        .perform(
            put(base + "/" + opportunityId)
                .with(opportunityWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{}"))
        .andExpect(status().isForbidden());
    mockMvc
        .perform(
            patch(base + "/" + opportunityId)
                .with(opportunityWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{}"))
        .andExpect(status().isForbidden());
  }

  @Test
  void rejectsInactiveParentsAndAnonymousOrWrongAuthority() throws Exception {
    Scope draft = seedDraftScope();
    mockMvc
        .perform(
            post(opportunitiesUrl(draft))
                .with(opportunityWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content(staticPayload("too-soon", "Avaliar proteção agrícola")))
        .andExpect(status().isUnprocessableEntity())
        .andExpect(jsonPath("$.code").value("INVALID_PARENT_STATE"));

    String correlation = "77777777-7777-4777-8777-777777777777";
    Scope active = seedActiveScope("auth-pub", "auth-ch", "auth-env");
    mockMvc
        .perform(get(opportunitiesUrl(active)).header("X-Correlation-ID", correlation))
        .andExpect(status().isUnauthorized())
        .andExpect(header().string("X-Correlation-ID", correlation))
        .andExpect(jsonPath("$.code").value("AUTHENTICATION_REQUIRED"))
        .andExpect(jsonPath("$.correlationId").value(correlation));

    mockMvc
        .perform(get(opportunitiesUrl(active)).with(catalogOnly()))
        .andExpect(status().isForbidden())
        .andExpect(jsonPath("$.code").value("ACCESS_DENIED"));

    mockMvc
        .perform(
            post(opportunitiesUrl(active))
                .with(opportunityReader())
                .contentType(MediaType.APPLICATION_JSON)
                .content(staticPayload("no-write", "Avaliar proteção agrícola")))
        .andExpect(status().isForbidden());

    mockMvc
        .perform(
            get(opportunitiesUrl(active))
                .with(
                    user("writer-only")
                        .authorities(
                            new SimpleGrantedAuthority(OpportunityAuthorities.WRITE))))
        .andExpect(status().isForbidden());
  }

  @Test
  void compositeOpportunityForeignKeysRejectCrossPublisher() {
    UUID publisherA = UUID.randomUUID();
    UUID publisherB = UUID.randomUUID();
    UUID channelA = UUID.randomUUID();
    UUID environmentA = UUID.randomUUID();
    jdbcTemplate.update(
        """
        INSERT INTO segsense.publisher
          (id, key, name, status, version, created_at, updated_at, created_by, updated_by)
        VALUES (?, 'fk-pub-a', 'Pub A', 'ACTIVE', 0, NOW(), NOW(), 'it', 'it')
        """,
        publisherA);
    jdbcTemplate.update(
        """
        INSERT INTO segsense.publisher
          (id, key, name, status, version, created_at, updated_at, created_by, updated_by)
        VALUES (?, 'fk-pub-b', 'Pub B', 'ACTIVE', 0, NOW(), NOW(), 'it', 'it')
        """,
        publisherB);
    jdbcTemplate.update(
        """
        INSERT INTO segsense.channel
          (id, publisher_id, key, name, type, status, version, created_at, updated_at, created_by, updated_by)
        VALUES (?, ?, 'fk-ch-a', 'Canal A', 'WEBSITE', 'ACTIVE', 0, NOW(), NOW(), 'it', 'it')
        """,
        channelA,
        publisherA);
    jdbcTemplate.update(
        """
        INSERT INTO segsense.contextual_environment
          (id, publisher_id, channel_id, key, name, type, status, version, created_at, updated_at, created_by, updated_by)
        VALUES (?, ?, ?, 'fk-env-a', 'Env A', 'PAGE', 'ACTIVE', 0, NOW(), NOW(), 'it', 'it')
        """,
        environmentA,
        publisherA,
        channelA);

    UUID ok = UUID.randomUUID();
    jdbcTemplate.update(
        """
        INSERT INTO segsense.contextual_opportunity
          (id, publisher_id, channel_id, environment_id, key, status, current_revision, version,
           created_at, updated_at, created_by, updated_by)
        VALUES (?, ?, ?, ?, 'fk-ok', 'DRAFT', 1, 0, NOW(), NOW(), 'it', 'it')
        """,
        ok,
        publisherA,
        channelA,
        environmentA);

    org.assertj.core.api.Assertions.assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    INSERT INTO segsense.contextual_opportunity
                      (id, publisher_id, channel_id, environment_id, key, status, current_revision, version,
                       created_at, updated_at, created_by, updated_by)
                    VALUES (?, ?, ?, ?, 'fk-bad', 'DRAFT', 1, 0, NOW(), NOW(), 'it', 'it')
                    """,
                    UUID.randomUUID(),
                    publisherB,
                    channelA,
                    environmentA))
        .isInstanceOf(org.springframework.dao.DataIntegrityViolationException.class);
  }

  private Scope seedActiveScope(String publisherKey, String channelKey, String environmentKey)
      throws Exception {
    String publisherBody =
        mockMvc
            .perform(
                post("/api/v1/admin/publishers")
                    .with(opportunityWriter())
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
                .with(opportunityWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"ACTIVE\",\"version\":" + publisherVersion + "}"))
        .andExpect(status().isOk());

    String channelBody =
        mockMvc
            .perform(
                post("/api/v1/admin/publishers/" + publisherId + "/channels")
                    .with(opportunityWriter())
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
                .with(opportunityWriter())
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
                    .with(opportunityWriter())
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
                    .with(opportunityWriter())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("{\"status\":\"ACTIVE\",\"version\":" + environmentVersion + "}"))
            .andExpect(status().isOk())
            .andReturn()
            .getResponse()
            .getContentAsString();
    long activeEnvironmentVersion = ((Number) JsonPath.read(activated, "$.version")).longValue();
    return new Scope(publisherId, channelId, environmentId, activeEnvironmentVersion);
  }

  private Scope seedDraftScope() throws Exception {
    String publisherBody =
        mockMvc
            .perform(
                post("/api/v1/admin/publishers")
                    .with(opportunityWriter())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("{\"key\":\"draft-pub\",\"name\":\"Publicador rascunho\"}"))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID publisherId = UUID.fromString(JsonPath.read(publisherBody, "$.id"));
    String channelBody =
        mockMvc
            .perform(
                post("/api/v1/admin/publishers/" + publisherId + "/channels")
                    .with(opportunityWriter())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("{\"key\":\"draft-ch\",\"name\":\"Canal rascunho\",\"type\":\"WEBSITE\"}"))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID channelId = UUID.fromString(JsonPath.read(channelBody, "$.id"));
    String environmentBody =
        mockMvc
            .perform(
                post("/api/v1/admin/publishers/"
                        + publisherId
                        + "/channels/"
                        + channelId
                        + "/environments")
                    .with(opportunityWriter())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("{\"key\":\"draft-env\",\"name\":\"Ambiente rascunho\",\"type\":\"PAGE\"}"))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID environmentId = UUID.fromString(JsonPath.read(environmentBody, "$.id"));
    return new Scope(publisherId, channelId, environmentId, 0L);
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

  private static String dynamicPayload(String key, boolean nonPersonal) {
    String fieldKey = nonPersonal ? "cropType" : "cpf";
    String label = nonPersonal ? "Tipo de cultura" : "Documento pessoal";
    return """
        {"key":"%s","title":"Proteção dinâmica xx","contextMode":"DYNAMIC",
         "contextSummaryTemplate":"Resumo para {{%s}} no ambiente.",
         "objectiveTemplate":"Quero avaliar proteção para {{%s}} neste contexto.",
         "callToActionLabel":"Avaliar",
         "contextFields":[{"key":"%s","label":"%s","type":"ENUM","required":true,
           "source":"PUBLISHER","classification":"NON_PERSONAL","allowedValues":["soja","milho"]}]}
        """
        .formatted(key, fieldKey, fieldKey, fieldKey, label);
  }

  private static String revisionPayload(
      long expectedVersion, int baseRevision, String title, String mode, String ignored) {
    return """
        {"expectedVersion":%s,"baseRevision":%s,"title":"%s","contextMode":"%s",
         "contextSummaryTemplate":"Resumo estático de contexto.",
         "objectiveTemplate":"Objetivo estático de avaliação.","callToActionLabel":"Avaliar"}
        """
        .formatted(expectedVersion, baseRevision, title, mode);
  }

  private static RequestPostProcessor opportunityWriter() {
    return user("opportunity-tester")
        .authorities(
            new SimpleGrantedAuthority(CatalogAuthorities.READ),
            new SimpleGrantedAuthority(CatalogAuthorities.WRITE),
            new SimpleGrantedAuthority(OpportunityAuthorities.READ),
            new SimpleGrantedAuthority(OpportunityAuthorities.WRITE));
  }

  private static RequestPostProcessor opportunityReader() {
    return user("opportunity-reader")
        .authorities(
            new SimpleGrantedAuthority(CatalogAuthorities.READ),
            new SimpleGrantedAuthority(OpportunityAuthorities.READ));
  }

  private static RequestPostProcessor catalogOnly() {
    return user("catalog-only")
        .authorities(
            new SimpleGrantedAuthority(CatalogAuthorities.READ),
            new SimpleGrantedAuthority(CatalogAuthorities.WRITE));
  }

  private record Scope(
      UUID publisherId, UUID channelId, UUID environmentId, long environmentVersion) {}
}
