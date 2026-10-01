package br.com.actionfinance;

import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.application.identity.AccessAdminService;
import br.com.actionfinance.application.identity.MembershipRole;
import br.com.actionfinance.application.integration.SpiderInteractionClient;
import br.com.actionfinance.application.integration.SpiderInteractionClient.SpiderListResult;
import br.com.actionfinance.support.AccessTestData;
import br.com.actionfinance.support.PostgresFoundationContainer;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.containers.wait.strategy.Wait;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.net.CookieManager;
import java.net.CookiePolicy;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.when;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.DEFINED_PORT, properties = "server.port=18792")
@ActiveProfiles("oidc-it")
@Testcontainers
class PayReceiptSyncOidcIT {

    private static final int APP_PORT = 18792;

    @Container
    static final PostgreSQLContainer<?> POSTGRES = PostgresFoundationContainer.create();

    @Container
    static final GenericContainer<?> IDP =
            new GenericContainer<>("ghcr.io/navikt/mock-oauth2-server:2.1.10")
                    .withExposedPorts(8080)
                    .withEnv("JSON_CONFIG", "{\"interactiveLogin\":false}")
                    .waitingFor(Wait.forHttp("/default/.well-known/openid-configuration").forStatusCode(200));

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry registry) {
        String issuer = "http://127.0.0.1:" + IDP.getMappedPort(8080) + "/default";
        String origin = "http://127.0.0.1:" + APP_PORT;
        registry.add("server.address", () -> "127.0.0.1");
        registry.add("actionfinance.demo-auth.enabled", () -> "false");
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", () -> "actionfinance_runtime");
        registry.add("spring.datasource.password", () -> "runtime-test");
        registry.add("spring.flyway.user", () -> "actionfinance_migrator");
        registry.add("spring.flyway.password", () -> "migrator-test");
        registry.add("spring.flyway.url", POSTGRES::getJdbcUrl);
        registry.add("actionfinance.public-origin", () -> origin);
        registry.add("actionfinance.oidc.enabled", () -> "true");
        registry.add("actionfinance.oidc.issuer", () -> issuer);
        registry.add("actionfinance.oidc.client-id", () -> "actionfinance");
        registry.add("actionfinance.oidc.client-secret", () -> "test-secret");
        registry.add("actionfinance.oidc.redirect-uri", () -> origin + "/login/oauth2/code/actionfinance");
        registry.add("spring.security.oauth2.client.registration.actionfinance.client-id", () -> "actionfinance");
        registry.add(
                "spring.security.oauth2.client.registration.actionfinance.client-secret", () -> "test-secret");
        registry.add(
                "spring.security.oauth2.client.registration.actionfinance.authorization-grant-type",
                () -> "authorization_code");
        registry.add("spring.security.oauth2.client.registration.actionfinance.scope", () -> "openid,profile");
        registry.add(
                "spring.security.oauth2.client.registration.actionfinance.redirect-uri",
                () -> origin + "/login/oauth2/code/actionfinance");
        registry.add("spring.security.oauth2.client.provider.actionfinance.issuer-uri", () -> issuer);
        registry.add("actionfinance.session.cookie-secure", () -> "false");
        registry.add("actionfinance.integration.homolog", () -> "false");
        registry.add("actionfinance.integration.receipt-sync-enabled", () -> "true");
        registry.add("actionfinance.integration.spider-monitor-base-url", () -> "https://monitor.spider.actionhub.com.br");
    }

    @LocalServerPort
    int port;

    @Autowired
    AccessAdminService admin;

    @Autowired
    JdbcTemplate jdbc;

    @MockBean
    SpiderInteractionClient spider;

    private final ObjectMapper mapper = new ObjectMapper();

    @BeforeEach
    void seed() {
        AccessTestData.seedCompanies(jdbc);
        jdbc.update(
                """
                insert into actionfinance.pay_company_mapping (
                    id, tenant_id, company_id, pay_app_id, environment, authorized, created_at, updated_at)
                values (?,?,?,?, 'HOMOLOG', true, now(), now())
                on conflict (tenant_id, company_id) do update set authorized = true
                """,
                UUID.fromString("9c2e0a10-aaaa-4b8a-9c2e-0a104f110801"),
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                "af-public-test-padaria");
        when(spider.list(any(), any(), any(), any(), any(), anyInt()))
                .thenReturn(
                        new SpiderListResult(
                                true,
                                "READY",
                                "spd-oidc",
                                "PRESENT_EXTERNAL_LIST",
                                "SATELLITE_CONTRACT_V1_4_THEN_CAPABILITY_RESOLUTION",
                                "LIST_PAYMENT_TRANSACTIONS",
                                "corr-oidc",
                                "afm-oidc",
                                "HOMOLOG",
                                0,
                                null,
                                List.of(),
                                null,
                                null));
    }

    @Test
    void oidcOperatorSyncsViewerAndOtherCompanyAreDeniedWithoutHomolog() throws Exception {
        String issuer = "http://127.0.0.1:" + IDP.getMappedPort(8080) + "/default";
        CookieManager cookies = new CookieManager(null, CookiePolicy.ACCEPT_ALL);
        HttpClient operator = client(cookies);
        followLogin(operator);
        String subject = me(operator).get("subject").asText();
        admin.provision(
                "Operador sync público",
                issuer,
                subject,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                MembershipRole.OPERATOR,
                "OIDC receipt sync",
                "test",
                null,
                false);

        JsonNode info = mapper.readTree(jsonGet(operator, "/api/v1/system/info").body());
        assertThat(info.get("homologIntegration").asBoolean()).isFalse();
        assertThat(info.get("receiptSyncEnabled").asBoolean()).isTrue();
        assertThat(info.get("demoEnvironment").asBoolean()).isFalse();
        assertThat(info.get("accessMode").asText()).isEqualTo("OIDC");

        HttpResponse<String> demoToken =
                HttpClient.newBuilder()
                        .followRedirects(HttpClient.Redirect.NEVER)
                        .build()
                        .send(
                                HttpRequest.newBuilder(uri("/api/v1/pay-receipts?companyId=" + DemoPrincipalCatalog.COMPANY_A))
                                        .header("Authorization", "Bearer operator-demo-token-aaaaaaaaaaaaaaaaaaaa")
                                        .GET()
                                        .build(),
                                HttpResponse.BodyHandlers.ofString());
        assertThat(demoToken.statusCode()).isEqualTo(401);

        assertThat(jsonGet(operator, "/api/v1/pay-receipts?companyId=" + DemoPrincipalCatalog.COMPANY_A).statusCode())
                .isEqualTo(200);
        assertThat(jsonGet(operator, "/api/v1/pay-receipts?companyId=" + DemoPrincipalCatalog.COMPANY_B).statusCode())
                .isEqualTo(403);

        HttpResponse<String> missingCsrf =
                operator.send(
                        HttpRequest.newBuilder(uri("/api/v1/pay-receipts/sync?companyId=" + DemoPrincipalCatalog.COMPANY_A))
                                .POST(HttpRequest.BodyPublishers.noBody())
                                .build(),
                        HttpResponse.BodyHandlers.ofString());
        assertThat(missingCsrf.statusCode()).isEqualTo(403);

        JsonNode csrf = mapper.readTree(jsonGet(operator, "/api/v1/access/csrf").body());
        HttpResponse<String> synced =
                operator.send(
                        HttpRequest.newBuilder(uri("/api/v1/pay-receipts/sync?companyId=" + DemoPrincipalCatalog.COMPANY_A))
                                .header(csrf.get("headerName").asText(), csrf.get("token").asText())
                                .POST(HttpRequest.BodyPublishers.noBody())
                                .build(),
                        HttpResponse.BodyHandlers.ofString());
        assertThat(synced.statusCode()).isEqualTo(200);
        assertThat(mapper.readTree(synced.body()).get("run").get("status").asText()).isIn("EMPTY", "SUCCESS");

        admin.provision(
                "Operador sync público",
                issuer,
                subject,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                MembershipRole.VIEWER,
                "Downgrade consulta",
                "test",
                null,
                false);
        JsonNode csrfViewer = mapper.readTree(jsonGet(operator, "/api/v1/access/csrf").body());
        HttpResponse<String> viewerWrite =
                operator.send(
                        HttpRequest.newBuilder(uri("/api/v1/pay-receipts/sync?companyId=" + DemoPrincipalCatalog.COMPANY_A))
                                .header(csrfViewer.get("headerName").asText(), csrfViewer.get("token").asText())
                                .POST(HttpRequest.BodyPublishers.noBody())
                                .build(),
                        HttpResponse.BodyHandlers.ofString());
        assertThat(viewerWrite.statusCode()).isEqualTo(403);
    }

    private void followLogin(HttpClient client) throws Exception {
        HttpResponse<String> started =
                client.send(
                        HttpRequest.newBuilder(uri("/oauth2/authorization/actionfinance")).GET().build(),
                        HttpResponse.BodyHandlers.ofString());
        assertThat(started.statusCode()).isLessThan(500);
        if (jsonGet(client, "/api/v1/access/me").statusCode() == 401) {
            throw new AssertionError("OIDC login did not establish a session");
        }
    }

    private JsonNode me(HttpClient client) throws Exception {
        HttpResponse<String> response = jsonGet(client, "/api/v1/access/me");
        assertThat(response.statusCode()).isEqualTo(200);
        return mapper.readTree(response.body());
    }

    private HttpResponse<String> jsonGet(HttpClient client, String path) throws Exception {
        return client.send(
                HttpRequest.newBuilder(uri(path)).header("Accept", "application/json").GET().build(),
                HttpResponse.BodyHandlers.ofString());
    }

    private URI uri(String path) {
        return URI.create("http://127.0.0.1:" + port + path);
    }

    private static HttpClient client(CookieManager cookies) {
        return HttpClient.newBuilder()
                .cookieHandler(cookies)
                .followRedirects(HttpClient.Redirect.ALWAYS)
                .connectTimeout(Duration.ofSeconds(15))
                .build();
    }
}
