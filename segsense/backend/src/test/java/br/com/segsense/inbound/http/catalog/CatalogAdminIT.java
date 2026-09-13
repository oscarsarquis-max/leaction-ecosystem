package br.com.segsense.inbound.http.catalog;

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
class CatalogAdminIT {

  @Container
  @ServiceConnection
  static PostgreSQLContainer postgres = new PostgreSQLContainer("postgres:18.6");

  @Autowired MockMvc mockMvc;
  @Autowired JdbcTemplate jdbcTemplate;

  @Test
  void appliesV2CatalogSchema() {
    Integer publishers =
        jdbcTemplate.queryForObject(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'segsense' AND table_name = 'publisher'
            """,
            Integer.class);
    Integer channels =
        jdbcTemplate.queryForObject(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'segsense' AND table_name = 'channel'
            """,
            Integer.class);
    Integer environments =
        jdbcTemplate.queryForObject(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'segsense' AND table_name = 'contextual_environment'
            """,
            Integer.class);
    assertThat(publishers).isEqualTo(1);
    assertThat(channels).isEqualTo(1);
    assertThat(environments).isEqualTo(1);
  }

  @Test
  void crudPaginationIsolationAndConflicts() throws Exception {
    String correlation = "44444444-4444-4444-8444-444444444444";
    String publisherBody =
        mockMvc
            .perform(
                post("/api/v1/admin/publishers")
                    .with(catalogWriter())
                    .header("X-Correlation-ID", correlation)
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(
                        """
                        {"key":"Acme-Midia","name":" Acme Mídia "}
                        """))
            .andExpect(status().isCreated())
            .andExpect(header().string("X-Correlation-ID", correlation))
            .andExpect(jsonPath("$.key").value("acme-midia"))
            .andExpect(jsonPath("$.name").value("Acme Mídia"))
            .andExpect(jsonPath("$.status").value("DRAFT"))
            .andExpect(jsonPath("$.correlationId").doesNotExist())
            .andReturn()
            .getResponse()
            .getContentAsString();

    UUID publisherId = UUID.fromString(JsonPath.read(publisherBody, "$.id"));
    long publisherVersion = ((Number) JsonPath.read(publisherBody, "$.version")).longValue();

    String duplicateBody =
        mockMvc
            .perform(
                post("/api/v1/admin/publishers")
                    .with(catalogWriter())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("{\"key\":\"acme-midia\",\"name\":\"Duplicado\"}"))
            .andExpect(status().isConflict())
            .andExpect(jsonPath("$.code").value("PUBLISHER_KEY_CONFLICT"))
            .andReturn()
            .getResponse()
            .getContentAsString();
    assertThat(duplicateBody)
        .doesNotContain("SQL", "duplicate key", "ERROR:", "javax.sql", "org.postgresql");

    mockMvc
        .perform(
            post("/api/v1/admin/publishers/" + publisherId + "/status")
                .with(catalogWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"ACTIVE\",\"version\":" + publisherVersion + "}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("ACTIVE"));

    String otherPublisherBody =
        mockMvc
            .perform(
                post("/api/v1/admin/publishers")
                    .with(catalogWriter())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("{\"key\":\"outro-pub\",\"name\":\"Outro Publicador\"}"))
            .andExpect(status().isCreated())
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID otherPublisherId = UUID.fromString(JsonPath.read(otherPublisherBody, "$.id"));

    String channelBody =
        mockMvc
            .perform(
                post("/api/v1/admin/publishers/" + publisherId + "/channels")
                    .with(catalogWriter())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(
                        """
                        {"key":"Portal","name":"Portal Web","type":"WEBSITE"}
                        """))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.key").value("portal"))
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID channelId = UUID.fromString(JsonPath.read(channelBody, "$.id"));
    long channelVersion = ((Number) JsonPath.read(channelBody, "$.version")).longValue();

    mockMvc
        .perform(
            post("/api/v1/admin/publishers/" + publisherId + "/channels/" + channelId + "/status")
                .with(catalogWriter())
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
                    .with(catalogWriter())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(
                        """
                        {"key":"Home","name":"Página inicial","type":"PAGE","canonicalUrl":"https://example.com/home"}
                        """))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.key").value("home"))
            .andExpect(jsonPath("$.effectivelyAvailable").value(false))
            .andReturn()
            .getResponse()
            .getContentAsString();
    UUID environmentId = UUID.fromString(JsonPath.read(environmentBody, "$.id"));

    mockMvc
        .perform(
            get("/api/v1/admin/publishers/" + otherPublisherId + "/channels/" + channelId)
                .with(catalogReader()))
        .andExpect(status().isNotFound())
        .andExpect(jsonPath("$.code").value("NOT_FOUND"));

    mockMvc
        .perform(
            get("/api/v1/admin/publishers/"
                    + otherPublisherId
                    + "/channels/"
                    + channelId
                    + "/environments/"
                    + environmentId)
                .with(catalogReader()))
        .andExpect(status().isNotFound());

    mockMvc
        .perform(
            patch("/api/v1/admin/publishers/" + publisherId)
                .with(catalogWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"name\":\"Acme Atualizado\",\"version\":0,\"key\":\"mutacao\"}"))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.code").value("CONCURRENT_MODIFICATION"));

    mockMvc
        .perform(
            patch("/api/v1/admin/publishers/" + publisherId)
                .with(catalogWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"name\":\"Acme Atualizado\",\"version\":1}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.name").value("Acme Atualizado"))
        .andExpect(jsonPath("$.key").value("acme-midia"));

    mockMvc
        .perform(
            post("/api/v1/admin/publishers/" + publisherId + "/status")
                .with(catalogWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"DRAFT\",\"version\":2}"))
        .andExpect(status().isUnprocessableEntity())
        .andExpect(jsonPath("$.code").value("INVALID_STATE_TRANSITION"));

    mockMvc
        .perform(
            post("/api/v1/admin/publishers")
                .with(catalogWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"key\":\"x\",\"name\":\"ab\"}"))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));

    mockMvc
        .perform(delete("/api/v1/admin/publishers/" + publisherId).with(catalogWriter()))
        .andExpect(status().isForbidden());
    mockMvc
        .perform(
            put("/api/v1/admin/publishers/" + publisherId)
                .with(catalogWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"key\":\"novo\",\"name\":\"Novo\"}"))
        .andExpect(status().isForbidden());

    mockMvc
        .perform(
            post("/api/v1/admin/publishers")
                .with(catalogWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"key\":\"pag-a\",\"name\":\"Página A\"}"))
        .andExpect(status().isCreated());
    mockMvc
        .perform(
            post("/api/v1/admin/publishers")
                .with(catalogWriter())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"key\":\"pag-b\",\"name\":\"Página B\"}"))
        .andExpect(status().isCreated());

    MvcResult firstPage =
        mockMvc
            .perform(get("/api/v1/admin/publishers").with(catalogReader()).queryParam("page[size]", "2"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.items.length()").value(2))
            .andExpect(jsonPath("$.page.size").value(2))
            .andExpect(jsonPath("$.page.next").isNotEmpty())
            .andReturn();
    String next = JsonPath.read(firstPage.getResponse().getContentAsString(), "$.page.next");
    mockMvc
        .perform(
            get("/api/v1/admin/publishers")
                .with(catalogReader())
                .queryParam("page[size]", "2")
                .queryParam("page[after]", next))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.items.length()").isNumber());
  }

  @Test
  void anonymousAdminIs401AndMissingAuthorityIs403() throws Exception {
    String correlation = "55555555-5555-4555-8555-555555555555";
    mockMvc
        .perform(get("/api/v1/admin/publishers").header("X-Correlation-ID", correlation))
        .andExpect(status().isUnauthorized())
        .andExpect(header().string("X-Correlation-ID", correlation))
        .andExpect(jsonPath("$.code").value("AUTHENTICATION_REQUIRED"))
        .andExpect(jsonPath("$.correlationId").value(correlation));

    mockMvc
        .perform(get("/api/v1/admin/publishers").with(user("tester")))
        .andExpect(status().isForbidden())
        .andExpect(jsonPath("$.code").value("ACCESS_DENIED"));

    mockMvc
        .perform(
            post("/api/v1/admin/publishers")
                .with(user("reader").authorities(new SimpleGrantedAuthority(CatalogAuthorities.READ)))
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"key\":\"somente-leitura\",\"name\":\"Somente leitura\"}"))
        .andExpect(status().isForbidden());

    mockMvc
        .perform(
            get("/api/v1/admin/publishers")
                .with(user("writer").authorities(new SimpleGrantedAuthority(CatalogAuthorities.WRITE))))
        .andExpect(status().isForbidden());
  }

  private static RequestPostProcessor catalogWriter() {
    return user("catalog-tester")
        .authorities(
            new SimpleGrantedAuthority(CatalogAuthorities.READ),
            new SimpleGrantedAuthority(CatalogAuthorities.WRITE));
  }

  private static RequestPostProcessor catalogReader() {
    return user("catalog-reader")
        .authorities(new SimpleGrantedAuthority(CatalogAuthorities.READ));
  }
}
