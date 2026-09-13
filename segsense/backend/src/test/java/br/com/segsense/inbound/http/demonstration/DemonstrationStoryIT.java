package br.com.segsense.inbound.http.demonstration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import br.com.segsense.infrastructure.security.DemonstrationAuthorities;
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
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
@Testcontainers
@ActiveProfiles("test")
class DemonstrationStoryIT {

  @Container
  @ServiceConnection
  static PostgreSQLContainer postgres = new PostgreSQLContainer("postgres:18.6");

  @Autowired MockMvc mockMvc;
  @Autowired JdbcTemplate jdbcTemplate;

  @Test
  void editorialCyclePublicIsolationAndSqlGuards() throws Exception {
    mockMvc
        .perform(get("/api/v1/admin/demonstrations"))
        .andExpect(status().isUnauthorized());
    mockMvc
        .perform(get("/api/v1/public/demonstrations/icatu-demonstracao"))
        .andExpect(status().isNotFound())
        .andExpect(header().string("Cache-Control", org.hamcrest.Matchers.containsString("no-store")))
        .andExpect(jsonPath("$.code").value("DEMONSTRATION_NOT_PUBLISHED"));

    mockMvc
        .perform(
            post("/api/v1/admin/demonstrations")
                .with(reader())
                .contentType(MediaType.APPLICATION_JSON)
                .content(createBody("icatu-demonstracao")))
        .andExpect(status().isForbidden());

    String created =
        mockMvc
            .perform(
                post("/api/v1/admin/demonstrations")
                    .with(writer())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(createBody("icatu-demonstracao")))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.workflowStatus").value("DRAFT"))
            .andExpect(jsonPath("$.publicationStatus").value("UNPUBLISHED"))
            .andExpect(jsonPath("$.administrativePreview").value(true))
            .andReturn()
            .getResponse()
            .getContentAsString();
    long version = ((Number) JsonPath.read(created, "$.version")).longValue();

    mockMvc
        .perform(
            post("/api/v1/admin/demonstrations")
                .with(writer())
                .contentType(MediaType.APPLICATION_JSON)
                .content(createBody("icatu-demonstracao")))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.code").value("DEMONSTRATION_KEY_CONFLICT"));

    mockMvc
        .perform(
            post("/api/v1/admin/demonstrations/icatu-demonstracao/draft")
                .with(writer())
                .contentType(MediaType.APPLICATION_JSON)
                .content(updateBody(version, "<script>alert(1)</script>")))
        .andExpect(status().isBadRequest());

    mockMvc
        .perform(
            post("/api/v1/admin/demonstrations/icatu-demonstracao/publish")
                .with(publisher())
                .contentType(MediaType.APPLICATION_JSON)
                .content(justification(version)))
        .andExpect(status().isUnprocessableEntity());

    mockMvc
        .perform(
            post("/api/v1/admin/demonstrations/icatu-demonstracao/submit")
                .with(writer())
                .contentType(MediaType.APPLICATION_JSON)
                .content(justification(version)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.workflowStatus").value("UNDER_REVIEW"));
    created =
        mockMvc
            .perform(get("/api/v1/admin/demonstrations/icatu-demonstracao").with(reader()))
            .andExpect(status().isOk())
            .andReturn()
            .getResponse()
            .getContentAsString();
    version = ((Number) JsonPath.read(created, "$.version")).longValue();

    mockMvc
        .perform(
            post("/api/v1/admin/demonstrations/icatu-demonstracao/approve")
                .with(writer())
                .contentType(MediaType.APPLICATION_JSON)
                .content(justification(version)))
        .andExpect(status().isForbidden());

    mockMvc
        .perform(
            post("/api/v1/admin/demonstrations/icatu-demonstracao/approve")
                .with(approverSameAsWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content(justification(version)))
        .andExpect(status().isForbidden());

    mockMvc
        .perform(
            post("/api/v1/admin/demonstrations/icatu-demonstracao/approve")
                .with(approver())
                .contentType(MediaType.APPLICATION_JSON)
                .content(justification(version)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.workflowStatus").value("APPROVED"));
    created =
        mockMvc
            .perform(get("/api/v1/admin/demonstrations/icatu-demonstracao").with(reader()))
            .andReturn()
            .getResponse()
            .getContentAsString();
    version = ((Number) JsonPath.read(created, "$.version")).longValue();
    UUID storyId = UUID.fromString(JsonPath.read(created, "$.id"));

    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    INSERT INTO segsense.demonstration_block
                    (id, story_id, revision_number, position, title, body)
                    VALUES (?, ?, 1, 9, 'extra', 'bloco extra apos congelamento')
                    """,
                    UUID.randomUUID(),
                    storyId))
        .hasMessageContaining("frozen");
    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    "UPDATE segsense.demonstration_revision SET title = 'hack' WHERE story_id = ?",
                    storyId))
        .hasMessageContaining("immutable");

    mockMvc
        .perform(
            post("/api/v1/admin/demonstrations/icatu-demonstracao/publish")
                .with(publisher())
                .contentType(MediaType.APPLICATION_JSON)
                .content(justification(version)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.publicationStatus").value("LIVE"));

    mockMvc
        .perform(get("/api/v1/public/demonstrations/icatu-demonstracao"))
        .andExpect(status().isOk())
        .andExpect(header().string("Cache-Control", org.hamcrest.Matchers.containsString("no-store")))
        .andExpect(jsonPath("$.key").value("icatu-demonstracao"))
        .andExpect(jsonPath("$.id").doesNotExist())
        .andExpect(jsonPath("$.createdBy").doesNotExist())
        .andExpect(jsonPath("$.claims").doesNotExist())
        .andExpect(jsonPath("$.references[0].url").value("https://portal-api.icatuseguros.com.br/"));

    created =
        mockMvc
            .perform(get("/api/v1/admin/demonstrations/icatu-demonstracao").with(reader()))
            .andReturn()
            .getResponse()
            .getContentAsString();
    version = ((Number) JsonPath.read(created, "$.version")).longValue();

    mockMvc
        .perform(
            post("/api/v1/admin/demonstrations/icatu-demonstracao/pause")
                .with(publisher())
                .contentType(MediaType.APPLICATION_JSON)
                .content(justification(version)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.publicationStatus").value("PAUSED"));
    mockMvc
        .perform(get("/api/v1/public/demonstrations/icatu-demonstracao"))
        .andExpect(status().isNotFound());

    Integer v12 =
        jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM segsense.flyway_schema_history WHERE version = '12'", Integer.class);
    assertThat(v12).isEqualTo(1);
    assertThat(
            jdbcTemplate.queryForObject(
                """
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema='segsense' AND table_name IN ('policy','quote','icatu_product','insurance_policy')
                """,
                Integer.class))
        .isZero();
  }

  @Test
  void cannotForceLiveWithoutApprovalDecision() {
    UUID storyId = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa");
    jdbcTemplate.execute(
        (org.springframework.jdbc.core.ConnectionCallback<Object>)
            connection -> {
              boolean previous = connection.getAutoCommit();
              connection.setAutoCommit(false);
              try (var statement = connection.createStatement()) {
                statement.execute(
                    """
                    INSERT INTO segsense.demonstration_story
                    (id, story_key, workflow_status, publication_status, current_revision, published_revision,
                     version, created_at, updated_at, created_by, updated_by)
                    VALUES ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'sql-rogue', 'APPROVED', 'UNPUBLISHED', 1, NULL,
                            0, NOW(), NOW(), 'sql', 'sql')
                    """);
                statement.execute(
                    """
                    INSERT INTO segsense.demonstration_revision
                    (id, story_id, revision_number, title, summary, intended_audience, scope_note, frozen, created_at, created_by)
                    VALUES ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 1,
                            'Titulo', 'Resumo editorial minimo.', 'Gestor',
                            'Cenario demonstrativo nao oficial.', TRUE, NOW(), 'sql')
                    """);
                connection.commit();
              } catch (Exception exception) {
                connection.rollback();
                throw exception;
              } finally {
                connection.setAutoCommit(previous);
              }
              return null;
            });
    assertThatThrownBy(
            () ->
                jdbcTemplate.update(
                    """
                    UPDATE segsense.demonstration_story
                       SET publication_status = 'LIVE', published_revision = 1
                     WHERE story_key = 'sql-rogue'
                    """))
        .hasMessageContaining("approval decision");
    assertThat(storyId).isNotNull();
  }

  private static String createBody(String key) {
    return """
        {"key":"%s",
         "title":"Cenario demonstrativo Icatu",
         "summary":"Possibilidade comercial e arquitetural, sem integracao operacional.",
         "intendedAudience":"Gestor comercial do SegSense",
         "scopeNote":"Cenario demonstrativo nao oficial. Nao e oferta, parceria ou servico da Icatu.",
         "blocks":[{"title":"Origem ilustrativa","body":"Artigo digital ficticio de risco agricola, sem cobertura da Icatu."}],
         "claims":[{"text":"O Hub publico da Icatu afirma que as APIs sao autenticadas.","sourceKey":"icatu-hub-home"}]}
        """.formatted(key);
  }

  private static String updateBody(long version, String title) {
    return """
        {"version":%s,
         "title":"%s",
         "summary":"Possibilidade comercial e arquitetural, sem integracao operacional.",
         "intendedAudience":"Gestor comercial do SegSense",
         "scopeNote":"Cenario demonstrativo nao oficial. Nao e oferta, parceria ou servico da Icatu.",
         "blocks":[{"title":"Origem ilustrativa","body":"Artigo digital ficticio de risco agricola, sem cobertura da Icatu."}],
         "claims":[{"text":"O Hub publico da Icatu afirma que as APIs sao autenticadas.","sourceKey":"icatu-hub-home"}]}
        """.formatted(version, title);
  }

  private static String justification(long version) {
    return """
        {"version":%s,"justification":"Justificativa editorial com dez caracteres."}
        """.formatted(version);
  }

  private static RequestPostProcessor writer() {
    return user("demo-writer")
        .authorities(
            new SimpleGrantedAuthority(DemonstrationAuthorities.READ),
            new SimpleGrantedAuthority(DemonstrationAuthorities.WRITE));
  }

  private static RequestPostProcessor reader() {
    return user("demo-reader").authorities(new SimpleGrantedAuthority(DemonstrationAuthorities.READ));
  }

  private static RequestPostProcessor approver() {
    return user("demo-approver")
        .authorities(
            new SimpleGrantedAuthority(DemonstrationAuthorities.READ),
            new SimpleGrantedAuthority(DemonstrationAuthorities.APPROVE));
  }

  private static RequestPostProcessor approverSameAsWriter() {
    return user("demo-writer")
        .authorities(
            new SimpleGrantedAuthority(DemonstrationAuthorities.READ),
            new SimpleGrantedAuthority(DemonstrationAuthorities.APPROVE));
  }

  private static RequestPostProcessor publisher() {
    return user("demo-publisher")
        .authorities(
            new SimpleGrantedAuthority(DemonstrationAuthorities.READ),
            new SimpleGrantedAuthority(DemonstrationAuthorities.PUBLISH));
  }
}
