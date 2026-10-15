package br.com.actionfinance;

import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.application.finance.LocalDemoSeed;
import br.com.actionfinance.application.finance.PartyImportService;
import br.com.actionfinance.support.PostgresFoundationContainer;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("local-demo")
@Testcontainers
class PartyDirectoryIT {

    private static final String OPERATOR = "operator-demo-token-aaaaaaaaaaaaaaaaaaaa";
    private static final String VIEWER_A = "viewer-a-demo-token-bbbbbbbbbbbbbbbbbbbb";
    private static final String VIEWER_B = "viewer-b-demo-token-cccccccccccccccccccc";

    @Container
    static final PostgreSQLContainer<?> POSTGRES = PostgresFoundationContainer.create();

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", () -> "actionfinance_runtime");
        registry.add("spring.datasource.password", () -> "runtime-test");
        registry.add("spring.flyway.user", () -> "actionfinance_migrator");
        registry.add("spring.flyway.password", () -> "migrator-test");
        registry.add("spring.flyway.url", POSTGRES::getJdbcUrl);
        registry.add("server.address", () -> "127.0.0.1");
        registry.add("actionfinance.demo-auth.enabled", () -> "true");
        registry.add("actionfinance.demo-auth.operator-a-token", () -> OPERATOR);
        registry.add("actionfinance.demo-auth.viewer-a-token", () -> VIEWER_A);
        registry.add("actionfinance.demo-auth.viewer-b-token", () -> VIEWER_B);
        registry.add("actionfinance.clock.zone", () -> "America/Sao_Paulo");
        registry.add("actionfinance.clock.fixed-instant", () -> "2026-09-15T15:00:00Z");
    }

    @Autowired
    MockMvc mockMvc;

    @Autowired
    ObjectMapper mapper;

    @Test
    void createsMinimumSupplierWithUnitAndPersonWithoutDocument() throws Exception {
        String supplier = mockMvc.perform(
                        post("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(
                                        """
                                        {
                                          "name":"Moinho Modelo",
                                          "personKind":"LEGAL",
                                          "supplier":true,
                                          "customer":false,
                                          "documentCountry":"BR",
                                          "documentType":"CNPJ",
                                          "documentNumber":"77.000.000/0001-16",
                                          "units":[{"name":"Depósito central","unitKind":"WAREHOUSE","primary":true}],
                                          "addresses":[{"country":"BR","postalCode":"01001-000","street":"Praça da Sé","number":"100","municipality":"São Paulo","region":"SP","usage":"MAIN"}]
                                        }
                                        """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.role").value("SUPPLIER"))
                .andExpect(jsonPath("$.documentPending").value(false))
                .andExpect(jsonPath("$.documentNumber").value("77.000.000/0001-16"))
                .andExpect(jsonPath("$.completeness.paymentReady").value(false))
                .andExpect(jsonPath("$.units[0].name").value("Depósito central"))
                .andReturn()
                .getResponse()
                .getContentAsString();
        JsonNode created = mapper.readTree(supplier);
        assertThat(created.get("id").asText()).isNotBlank();

        mockMvc.perform(
                        post("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"name\":\"João Produtor\",\"personKind\":\"NATURAL\",\"supplier\":true}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.documentPending").value(true));

        mockMvc.perform(
                        post("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"name\":\"Cliente e fornecedor\",\"customer\":true,\"supplier\":true}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.role").value("BOTH"));

        mockMvc.perform(
                        post("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"name\":\"\",\"supplier\":true}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fields.name").exists());
    }

    @Test
    void duplicateDocumentConflictsAndNameOnlySuggests() throws Exception {
        mockMvc.perform(
                        post("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(
                                        """
                                        {"name":"Doc Único","supplier":true,"documentCountry":"BR","documentType":"CNPJ","documentNumber":"11222333000181"}
                                        """))
                .andExpect(status().isOk());
        mockMvc.perform(
                        post("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(
                                        """
                                        {"name":"Outro nome","supplier":true,"documentCountry":"BR","documentType":"CNPJ","documentNumber":"11.222.333/0001-81"}
                                        """))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("CATALOG_CONFLICT"));

        mockMvc.perform(
                        get("/api/v1/catalogs/party-candidates")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("name", "Doc Único")
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].matchKind").value("NAME"));
    }

    @Test
    void concurrentSameDocumentCreatesOnlyOne() throws Exception {
        String body =
                """
                {"name":"Concorrente","supplier":true,"documentCountry":"BR","documentType":"CNPJ","documentNumber":"99.888.777/0001-00"}
                """;
        var pool = Executors.newFixedThreadPool(2);
        CountDownLatch start = new CountDownLatch(1);
        AtomicInteger ok = new AtomicInteger();
        AtomicInteger conflict = new AtomicInteger();
        Runnable task = () -> {
            try {
                start.await(5, TimeUnit.SECONDS);
                int status = mockMvc.perform(
                                post("/api/v1/catalogs/parties")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .header("Authorization", "Bearer " + OPERATOR)
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content(body))
                        .andReturn()
                        .getResponse()
                        .getStatus();
                if (status == 200) {
                    ok.incrementAndGet();
                } else if (status == 409) {
                    conflict.incrementAndGet();
                }
            } catch (Exception ex) {
                throw new IllegalStateException(ex);
            }
        };
        var first = pool.submit(task);
        var second = pool.submit(task);
        start.countDown();
        first.get(10, TimeUnit.SECONDS);
        second.get(10, TimeUnit.SECONDS);
        pool.shutdown();
        assertThat(ok.get()).isEqualTo(1);
        assertThat(conflict.get()).isEqualTo(1);
    }

    @Test
    void inactivatesReferencedPartyWithoutDeletingTitles() throws Exception {
        JsonNode current = mapper.readTree(
                mockMvc.perform(
                                get("/api/v1/catalogs/parties/" + LocalDemoSeed.CP_PADARIA_FORNECEDOR)
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .header("Authorization", "Bearer " + OPERATOR))
                        .andExpect(status().isOk())
                        .andExpect(jsonPath("$.referencedByTitles").value(true))
                        .andReturn()
                        .getResponse()
                        .getContentAsString());
        mockMvc.perform(
                        put("/api/v1/catalogs/parties/" + LocalDemoSeed.CP_PADARIA_FORNECEDOR)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"name\":\"Fornecedor Padaria\",\"supplier\":true,\"active\":false,\"version\":"
                                        + current.get("version").asLong() + "}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.active").value(false));
        mockMvc.perform(
                        get("/api/v1/payables/" + LocalDemoSeed.TITLE_PAG_PURCHASE)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.counterpartyId").value(LocalDemoSeed.CP_PADARIA_FORNECEDOR.toString()));
    }

    @Test
    void isolatesCompaniesAndBlocksViewerWrite() throws Exception {
        mockMvc.perform(
                        post("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + VIEWER_A)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"name\":\"Indevido\",\"customer\":true}"))
                .andExpect(status().isForbidden());
        mockMvc.perform(
                        get("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + VIEWER_B))
                .andExpect(status().isForbidden());
        JsonNode page = mapper.readTree(
                mockMvc.perform(
                                get("/api/v1/catalogs/parties")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .param("size", "1")
                                        .header("Authorization", "Bearer " + VIEWER_A))
                        .andExpect(status().isOk())
                        .andReturn()
                        .getResponse()
                        .getContentAsString());
        assertThat(page.get("totalItems").asInt()).isGreaterThan(page.get("items").size());
        assertThat(page.get("items").get(0).has("documentNumber")).isFalse();
    }

    @Test
    void importPreviewDoesNotWriteAndConfirmIsPerLineAndIdempotent() throws Exception {
        String csv = PartyImportService.TEMPLATE;
        JsonNode preview = mapper.readTree(
                mockMvc.perform(
                                post("/api/v1/catalogs/party-imports")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .header("Authorization", "Bearer " + OPERATOR)
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content("{\"filename\":\"modelo.csv\",\"csvText\":"
                                                + mapper.writeValueAsString(csv) + "}"))
                        .andExpect(status().isOk())
                        .andExpect(jsonPath("$.status").value("PREVIEW"))
                        .andExpect(jsonPath("$.atomicity").value("PER_LINE"))
                        .andReturn()
                        .getResponse()
                        .getContentAsString());
        mockMvc.perform(
                        get("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("q", "Padaria Modelo")
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalItems").value(0));

        String batchId = preview.get("id").asText();
        String decisions = """
                {"lines":[
                  {"id":"%s","selected":true,"resolution":"CREATE"},
                  {"id":"%s","selected":false,"resolution":"SKIP"}
                ]}
                """.formatted(preview.get("lines").get(0).get("id").asText(), preview.get("lines").get(1).get("id").asText());
        JsonNode first = mapper.readTree(
                mockMvc.perform(
                                post("/api/v1/catalogs/party-imports/" + batchId + "/confirm")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .header("Authorization", "Bearer " + OPERATOR)
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content(decisions))
                        .andExpect(status().isOk())
                        .andReturn()
                        .getResponse()
                        .getContentAsString());
        assertThat(first.get("report").get("created").asInt()).isEqualTo(1);
        assertThat(first.get("report").get("partial").asBoolean()).isTrue();

        JsonNode second = mapper.readTree(
                mockMvc.perform(
                                post("/api/v1/catalogs/party-imports/" + batchId + "/confirm")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .header("Authorization", "Bearer " + OPERATOR)
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content(decisions))
                        .andExpect(status().isOk())
                        .andReturn()
                        .getResponse()
                        .getContentAsString());
        assertThat(second.get("report").get("created").asInt()).isEqualTo(1);

        mockMvc.perform(
                        get("/api/v1/catalogs/counterparties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("compatibleWith", "PAYABLE")
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isArray());
        mockMvc.perform(
                        post("/api/v1/catalogs/counterparties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"name\":\"Via título\",\"role\":\"CUSTOMER\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("Via título"));
    }

    @Test
    void rejectsInvalidDocumentAndCrossPartyUnitAddress() throws Exception {
        mockMvc.perform(
                        post("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(
                                        """
                                        {"name":"Inválido","supplier":true,"personKind":"LEGAL","documentCountry":"BR","documentType":"CNPJ","documentNumber":"12.ABC.345/0001-95"}
                                        """))
                .andExpect(status().isBadRequest());

        String ownerJson = mockMvc.perform(
                        post("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(
                                        """
                                        {"name":"Dono da unidade","supplier":true,"units":[{"name":"Loja A","unitKind":"STORE","primary":true}]}
                                        """))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        String unitId = mapper.readTree(ownerJson).get("units").get(0).get("id").asText();
        mockMvc.perform(
                        post("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(
                                        "{\"name\":\"Outra pessoa\",\"supplier\":true,\"addresses\":[{\"country\":\"BR\",\"unitId\":\""
                                                + unitId
                                                + "\",\"street\":\"Rua X\"}]}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fields['addresses[0].unitId']").exists());
    }

    @Test
    void documentClaimBlocksOtherPersonAndAllowsPrimaryMirror() throws Exception {
        mockMvc.perform(
                        post("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(
                                        """
                                        {
                                          "name":"Matriz Espelho",
                                          "personKind":"LEGAL",
                                          "supplier":true,
                                          "documentCountry":"BR",
                                          "documentType":"CNPJ",
                                          "documentNumber":"20.000.000/0001-07",
                                          "units":[{"name":"Sede","unitKind":"OFFICE","primary":true,"documentCountry":"BR","documentType":"CNPJ","documentNumber":"20.000.000/0001-07"}]
                                        }
                                        """))
                .andExpect(status().isOk());
        mockMvc.perform(
                        post("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(
                                        """
                                        {"name":"Tentativa filial alheia","supplier":true,"units":[{"name":"Filial","unitKind":"STORE","primary":true,"documentCountry":"BR","documentType":"CNPJ","documentNumber":"20.000.000/0001-07"}]}
                                        """))
                .andExpect(status().isBadRequest());
    }

    @Test
    void legacyPatchKeepsNewFieldsAndMasksForViewer() throws Exception {
        JsonNode created = mapper.readTree(
                mockMvc.perform(
                                post("/api/v1/catalogs/parties")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .header("Authorization", "Bearer " + OPERATOR)
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content(
                                                """
                                                {"name":"Legado","personKind":"LEGAL","supplier":true,"documentCountry":"BR","documentType":"CNPJ","documentNumber":"33.000.000/0001-40"}
                                                """))
                        .andExpect(status().isOk())
                        .andReturn()
                        .getResponse()
                        .getContentAsString());
        mockMvc.perform(
                        patch("/api/v1/catalogs/counterparties/" + created.get("id").asText())
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"name\":\"Legado atualizado\",\"version\":" + created.get("version").asLong() + "}"))
                .andExpect(status().isOk());
        mockMvc.perform(
                        get("/api/v1/catalogs/parties/" + created.get("id").asText())
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("Legado atualizado"))
                .andExpect(jsonPath("$.documentNumber").value("33.000.000/0001-40"))
                .andExpect(jsonPath("$.personKind").value("LEGAL"));
        mockMvc.perform(
                        get("/api/v1/catalogs/party-candidates")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .param("documentCountry", "BR")
                                .param("documentType", "CNPJ")
                                .param("documentNumber", "33.000.000/0001-40")
                                .header("Authorization", "Bearer " + VIEWER_A))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].documentDisplay").value("••••40"));
    }

    @Test
    void externalIdentityUniqueWhenConnectionBlank() throws Exception {
        String body =
                """
                {"name":"Ext A","supplier":true,"externalIdentities":[{"originSystem":"FILE","externalId":"EXT-CONC-1"}]}
                """;
        mockMvc.perform(
                        post("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(body))
                .andExpect(status().isOk());
        mockMvc.perform(
                        post("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(
                                        """
                                        {"name":"Ext B","supplier":true,"externalIdentities":[{"originSystem":"FILE","externalId":"EXT-CONC-1"}]}
                                        """))
                .andExpect(status().isConflict());
    }

    @Test
    void importNameHomonymRequiresReviewAndRepeatAfterConfirmIsNewPreview() throws Exception {
        String csv =
                """
                nome;relacao;tipo_pessoa;pais_documento;tipo_documento;documento
                Padaria Repeat 012;FORNECEDOR;JURIDICA;BR;CNPJ;55.000.000/0001-83
                Joao Homônimo;FORNECEDOR;FISICA;BR;;;
                """;
        JsonNode first = mapper.readTree(
                mockMvc.perform(
                                post("/api/v1/catalogs/party-imports")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .header("Authorization", "Bearer " + OPERATOR)
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content("{\"filename\":\"modelo.csv\",\"csvText\":"
                                                + mapper.writeValueAsString(csv) + "}"))
                        .andExpect(status().isOk())
                        .andReturn()
                        .getResponse()
                        .getContentAsString());
        String decisions = """
                {"lines":[{"id":"%s","selected":true,"resolution":"CREATE"},{"id":"%s","selected":false,"resolution":"SKIP"}]}
                """.formatted(first.get("lines").get(0).get("id").asText(), first.get("lines").get(1).get("id").asText());
        mockMvc.perform(
                        post("/api/v1/catalogs/party-imports/" + first.get("id").asText() + "/confirm")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(decisions))
                .andExpect(status().isOk());
        JsonNode second = mapper.readTree(
                mockMvc.perform(
                                post("/api/v1/catalogs/party-imports")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .header("Authorization", "Bearer " + OPERATOR)
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content("{\"filename\":\"modelo.csv\",\"csvText\":"
                                                + mapper.writeValueAsString(csv) + "}"))
                        .andExpect(status().isOk())
                        .andReturn()
                        .getResponse()
                        .getContentAsString());
        assertThat(second.get("id").asText()).isNotEqualTo(first.get("id").asText());
        assertThat(second.get("lines").get(0).get("classification").asText()).isIn("DUPLICATE", "CONFLICT");
        assertThat(second.get("lines").get(0).get("selected").asBoolean()).isFalse();
        assertThat(second.get("lines").get(0).get("documentDisplay").asText()).startsWith("••••");
    }

    @Test
    void externalIdentityUniqueWhenConnectionPresentConcurrently() throws Exception {
        String body =
                """
                {"name":"Ext Conn","supplier":true,"externalIdentities":[{"originSystem":"PANNE","connectionKey":"conn-012","externalId":"EXT-CONC-2"}]}
                """;
        var pool = Executors.newFixedThreadPool(2);
        CountDownLatch start = new CountDownLatch(1);
        AtomicInteger ok = new AtomicInteger();
        AtomicInteger conflict = new AtomicInteger();
        Runnable task = () -> {
            try {
                start.await(5, TimeUnit.SECONDS);
                int status = mockMvc.perform(
                                post("/api/v1/catalogs/parties")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .header("Authorization", "Bearer " + OPERATOR)
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content(body))
                        .andReturn()
                        .getResponse()
                        .getStatus();
                if (status == 200) {
                    ok.incrementAndGet();
                } else if (status == 409) {
                    conflict.incrementAndGet();
                }
            } catch (Exception ex) {
                throw new IllegalStateException(ex);
            }
        };
        var first = pool.submit(task);
        var second = pool.submit(task);
        start.countDown();
        first.get(10, TimeUnit.SECONDS);
        second.get(10, TimeUnit.SECONDS);
        pool.shutdown();
        assertThat(ok.get()).isEqualTo(1);
        assertThat(conflict.get()).isEqualTo(1);
    }

    @Test
    void importRejectsStalePreviewVersion() throws Exception {
        JsonNode created = mapper.readTree(
                mockMvc.perform(
                                post("/api/v1/catalogs/parties")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .header("Authorization", "Bearer " + OPERATOR)
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content(
                                                """
                                                {"name":"Cadastro Versao 012","personKind":"LEGAL","supplier":true,"documentCountry":"BR","documentType":"CNPJ","documentNumber":"66.000.000/0001-08"}
                                                """))
                        .andExpect(status().isOk())
                        .andReturn()
                        .getResponse()
                        .getContentAsString());
        String csv =
                """
                nome;relacao;tipo_pessoa;pais_documento;tipo_documento;documento
                Cadastro Versao 012;FORNECEDOR;JURIDICA;BR;CNPJ;66.000.000/0001-08
                """;
        JsonNode preview = mapper.readTree(
                mockMvc.perform(
                                post("/api/v1/catalogs/party-imports")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .header("Authorization", "Bearer " + OPERATOR)
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content("{\"filename\":\"versao.csv\",\"csvText\":"
                                                + mapper.writeValueAsString(csv) + "}"))
                        .andExpect(status().isOk())
                        .andReturn()
                        .getResponse()
                        .getContentAsString());
        mockMvc.perform(
                        put("/api/v1/catalogs/parties/" + created.get("id").asText())
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(
                                        "{\"name\":\"Cadastro Versao 012 alterado\",\"supplier\":true,\"documentCountry\":\"BR\",\"documentType\":\"CNPJ\",\"documentNumber\":\"66.000.000/0001-08\",\"version\":"
                                                + created.get("version").asLong()
                                                + "}"))
                .andExpect(status().isOk());
        JsonNode confirmed = mapper.readTree(
                mockMvc.perform(
                                post("/api/v1/catalogs/party-imports/" + preview.get("id").asText() + "/confirm")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .header("Authorization", "Bearer " + OPERATOR)
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content(
                                                """
                                                {"lines":[{"id":"%s","selected":true,"resolution":"ENRICH"}]}
                                                """.formatted(preview.get("lines").get(0).get("id").asText())))
                        .andExpect(status().isOk())
                        .andReturn()
                        .getResponse()
                        .getContentAsString());
        assertThat(confirmed.get("lines").get(0).get("result").asText()).isEqualTo("REJECTED");
        assertThat(confirmed.get("lines").get(0).get("errorMessage").asText()).contains("mudou desde a prévia");
    }

    @Test
    void persistsFullPartyReloadsAfterEditAndKeepsTitleQuickCreate() throws Exception {
        JsonNode created = mapper.readTree(
                mockMvc.perform(
                                post("/api/v1/catalogs/parties")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .header("Authorization", "Bearer " + OPERATOR)
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content(
                                                """
                                                {
                                                  "name":"Fornecedor jornada 013",
                                                  "personKind":"LEGAL",
                                                  "supplier":true,
                                                  "documentCountry":"BR",
                                                  "documentType":"CNPJ",
                                                  "documentNumber":"88.000.000/0001-32",
                                                  "units":[{"name":"Sede 013","unitKind":"OFFICE","primary":true,"documentCountry":"BR","documentType":"CNPJ","documentNumber":"88.000.000/0001-32"}],
                                                  "addresses":[{"country":"BR","postalCode":"01001-000","street":"Praça da Sé","number":"100","municipality":"São Paulo","region":"SP","usage":"MAIN"}],
                                                  "contacts":[{"name":"Ana Jornada","email":"ana.jornada@example.test","primary":true}],
                                                  "supplies":[{"description":"Farinha 013","supplyCategory":"Insumos"}]
                                                }
                                                """))
                        .andExpect(status().isOk())
                        .andExpect(jsonPath("$.id").isNotEmpty())
                        .andExpect(jsonPath("$.name").value("Fornecedor jornada 013"))
                        .andExpect(jsonPath("$.units[0].name").value("Sede 013"))
                        .andExpect(jsonPath("$.addresses[0].street").value("Praça da Sé"))
                        .andExpect(jsonPath("$.contacts[0].name").value("Ana Jornada"))
                        .andExpect(jsonPath("$.supplies[0].description").value("Farinha 013"))
                        .andReturn()
                        .getResponse()
                        .getContentAsString());
        String id = created.get("id").asText();
        assertThat(id).isNotBlank();

        mockMvc.perform(
                        get("/api/v1/catalogs/parties/" + id)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(id))
                .andExpect(jsonPath("$.documentNumber").value("88.000.000/0001-32"));

        mockMvc.perform(
                        put("/api/v1/catalogs/parties/" + id)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(
                                        """
                                        {
                                          "name":"Fornecedor jornada 013 editado",
                                          "personKind":"LEGAL",
                                          "supplier":true,
                                          "documentCountry":"BR",
                                          "documentType":"CNPJ",
                                          "documentNumber":"88.000.000/0001-32",
                                          "version":%s
                                        }
                                        """.formatted(created.get("version").asLong())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("Fornecedor jornada 013 editado"));

        mockMvc.perform(
                        get("/api/v1/catalogs/parties/" + id)
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("Fornecedor jornada 013 editado"))
                .andExpect(jsonPath("$.documentNumber").value("88.000.000/0001-32"));

        JsonNode quick = mapper.readTree(
                mockMvc.perform(
                                post("/api/v1/catalogs/counterparties")
                                        .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                        .header("Authorization", "Bearer " + OPERATOR)
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content("{\"name\":\"Via titulo 013\",\"role\":\"SUPPLIER\"}"))
                        .andExpect(status().isOk())
                        .andExpect(jsonPath("$.name").value("Via titulo 013"))
                        .andReturn()
                        .getResponse()
                        .getContentAsString());
        mockMvc.perform(
                        get("/api/v1/catalogs/parties/" + quick.get("id").asText())
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.documentPending").value(true))
                .andExpect(jsonPath("$.name").value("Via titulo 013"));
    }

    @Test
    void sameNumberDifferentCountryIsNotMirrorAndTwoPrimariesAreRejected() throws Exception {
        mockMvc.perform(
                        post("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(
                                        """
                                        {
                                          "name":"Identidade cruzada 013",
                                          "personKind":"LEGAL",
                                          "supplier":true,
                                          "documentCountry":"BR",
                                          "documentType":"CNPJ",
                                          "documentNumber":"44.000.000/0001-67",
                                          "units":[{"name":"Exterior","unitKind":"OTHER","primary":true,"documentCountry":"US","documentType":"OTHER","documentNumber":"44000000000167"}]
                                        }
                                        """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.units[0].documentCountry").value("US"));

        mockMvc.perform(
                        post("/api/v1/catalogs/parties")
                                .param("companyId", DemoPrincipalCatalog.COMPANY_A.toString())
                                .header("Authorization", "Bearer " + OPERATOR)
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(
                                        """
                                        {
                                          "name":"Duas principais",
                                          "supplier":true,
                                          "units":[
                                            {"name":"A","unitKind":"STORE","primary":true},
                                            {"name":"B","unitKind":"STORE","primary":true}
                                          ]
                                        }
                                        """))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fields.units").exists());
    }
}
