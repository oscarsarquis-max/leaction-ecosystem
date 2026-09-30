package br.com.actionfinance;

import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.application.identity.AccessAdminService;
import br.com.actionfinance.application.identity.MembershipRole;
import br.com.actionfinance.support.AccessTestData;
import br.com.actionfinance.support.PostgresFoundationContainer;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
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
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.DEFINED_PORT, properties = "server.port=18791")
@ActiveProfiles("oidc-it")
@Testcontainers
class OidcAuthorizationCodeIT {

    private static final int APP_PORT = 18791;

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
    }

    @LocalServerPort
    int port;

    @Autowired
    AccessAdminService admin;

    @Autowired
    JdbcTemplate jdbc;

    private final ObjectMapper mapper = new ObjectMapper();

    @BeforeEach
    void seed() {
        AccessTestData.seedCompanies(jdbc);
    }

    @Test
    void authorizationCodeLoginSessionCsrfAndLocalAuthorization() throws Exception {
        String issuer = "http://127.0.0.1:" + IDP.getMappedPort(8080) + "/default";
        CookieManager unprovisionedCookies = new CookieManager(null, CookiePolicy.ACCEPT_ALL);
        HttpClient unprovisioned = client(unprovisionedCookies);
        followLogin(unprovisioned);
        JsonNode pending = me(unprovisioned);
        assertThat(pending.get("accessState").asText()).isEqualTo("NOT_PROVISIONED");
        assertThat(pending.get("authorizedCompanies").size()).isZero();
        String subject = pending.get("subject").asText();
        assertThat(subject).isNotBlank();
        assertThat(pending.get("issuer").asText()).isEqualTo(issuer);

        assertThat(jsonGet(unprovisioned, "/api/v1/receivables?companyId=" + DemoPrincipalCatalog.COMPANY_A).statusCode())
                .isEqualTo(403);

        admin.provision(
                "Operadora duas empresas",
                issuer,
                subject,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                MembershipRole.OPERATOR,
                "Prova do fluxo OIDC",
                "test",
                null,
                false);
        admin.provision(
                "Operadora duas empresas",
                issuer,
                subject,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_C,
                MembershipRole.OPERATOR,
                "Segunda empresa",
                "test",
                null,
                false);

        HttpClient operator = unprovisioned;
        CookieManager operatorCookies = unprovisionedCookies;
        JsonNode ready = me(operator);
        assertThat(ready.get("accessState").asText()).isEqualTo("READY");
        assertThat(ready.get("authorizedCompanies").size()).isEqualTo(2);

        HttpClient anonymous = HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NEVER).build();
        HttpResponse<String> demoToken =
                anonymous.send(
                        HttpRequest.newBuilder(uri("/api/v1/access/me"))
                                .header("Authorization", "Bearer demo-token-should-not-work-in-oidc")
                                .GET()
                                .build(),
                        HttpResponse.BodyHandlers.ofString());
        assertThat(demoToken.statusCode()).isEqualTo(401);

        JsonNode csrf = mapper.readTree(jsonGet(operator, "/api/v1/access/csrf").body());
        String token = csrf.get("token").asText();
        String header = csrf.get("headerName").asText();
        HttpResponse<String> missingCsrf =
                operator.send(
                        HttpRequest.newBuilder(uri("/logout")).POST(HttpRequest.BodyPublishers.noBody()).build(),
                        HttpResponse.BodyHandlers.ofString());
        assertThat(missingCsrf.statusCode()).isEqualTo(403);

        HttpClient noFollow =
                HttpClient.newBuilder()
                        .cookieHandler(operatorCookies)
                        .followRedirects(HttpClient.Redirect.NEVER)
                        .connectTimeout(Duration.ofSeconds(15))
                        .build();
        HttpResponse<String> logout =
                noFollow.send(
                        HttpRequest.newBuilder(uri("/logout"))
                                .header(header, token)
                                .POST(HttpRequest.BodyPublishers.noBody())
                                .build(),
                        HttpResponse.BodyHandlers.ofString());
        assertThat(logout.statusCode()).isEqualTo(302);
        assertThat(meStatus(operator)).isEqualTo(401);

        Optional<String> sessionCookie =
                operatorCookies.getCookieStore().get(uri("/")).stream()
                        .filter(cookie -> "AFSESSION".equalsIgnoreCase(cookie.getName()))
                        .findFirst()
                        .map(java.net.HttpCookie::getValue);
        assertThat(sessionCookie).isEmpty();
    }

    @Test
    void mixedRolesAcrossTenantsRevokeAndJsonLogout() throws Exception {
        String issuer = "http://127.0.0.1:" + IDP.getMappedPort(8080) + "/default";
        CookieManager cookies = new CookieManager(null, CookiePolicy.ACCEPT_ALL);
        HttpClient client = client(cookies);
        followLogin(client);
        String subject = me(client).get("subject").asText();
        admin.provision(
                "Operadora mista",
                issuer,
                subject,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                MembershipRole.OPERATOR,
                "Papel operador em A",
                "test",
                null,
                false);
        admin.provision(
                "Operadora mista",
                issuer,
                subject,
                DemoPrincipalCatalog.TENANT_B,
                DemoPrincipalCatalog.COMPANY_B,
                MembershipRole.VIEWER,
                "Papel consulta em B",
                "test",
                null,
                false);
        JsonNode profile = me(client);
        assertThat(profile.get("authorizedCompanies").size()).isEqualTo(2);
        assertThat(jsonGet(client, "/api/v1/receivables?companyId=" + DemoPrincipalCatalog.COMPANY_A).statusCode())
                .isEqualTo(200);
        assertThat(jsonGet(client, "/api/v1/receivables?companyId=" + DemoPrincipalCatalog.COMPANY_B).statusCode())
                .isEqualTo(200);

        JsonNode csrf = mapper.readTree(jsonGet(client, "/api/v1/access/csrf").body());
        HttpResponse<String> writeB =
                client.send(
                        HttpRequest.newBuilder(uri("/api/v1/receivables?companyId=" + DemoPrincipalCatalog.COMPANY_B + "&register=true"))
                                .header("Content-Type", "application/json")
                                .header("Idempotency-Key", "oidc-mixed-b")
                                .header(csrf.get("headerName").asText(), csrf.get("token").asText())
                                .POST(HttpRequest.BodyPublishers.ofString("{\"description\":\"nao\",\"amountMinor\":\"1000\",\"currency\":\"BRL\"}"))
                                .build(),
                        HttpResponse.BodyHandlers.ofString());
        assertThat(writeB.statusCode()).isEqualTo(403);

        admin.provision(
                "Operadora mista",
                issuer,
                subject,
                DemoPrincipalCatalog.TENANT_A,
                DemoPrincipalCatalog.COMPANY_A,
                MembershipRole.VIEWER,
                "Downgrade para consulta",
                "test",
                null,
                false);
        HttpResponse<String> writeAAfterDowngrade =
                client.send(
                        HttpRequest.newBuilder(uri("/api/v1/receivables?companyId=" + DemoPrincipalCatalog.COMPANY_A + "&register=true"))
                                .header("Content-Type", "application/json")
                                .header("Idempotency-Key", "oidc-mixed-a")
                                .header(csrf.get("headerName").asText(), csrf.get("token").asText())
                                .POST(HttpRequest.BodyPublishers.ofString("{\"description\":\"nao\",\"amountMinor\":\"1000\",\"currency\":\"BRL\"}"))
                                .build(),
                        HttpResponse.BodyHandlers.ofString());
        assertThat(writeAAfterDowngrade.statusCode()).isEqualTo(403);

        UUID userId = admin.provision(
                        "Operadora mista",
                        issuer,
                        subject,
                        DemoPrincipalCatalog.TENANT_B,
                        DemoPrincipalCatalog.COMPANY_B,
                        MembershipRole.VIEWER,
                        "obter userId",
                        "test",
                        null,
                        true)
                .userId();
        admin.revoke(userId, DemoPrincipalCatalog.TENANT_B, DemoPrincipalCatalog.COMPANY_B, "Revogacao B", "test", false);
        assertThat(jsonGet(client, "/api/v1/receivables?companyId=" + DemoPrincipalCatalog.COMPANY_B).statusCode())
                .isEqualTo(403);

        JsonNode csrf2 = mapper.readTree(jsonGet(client, "/api/v1/access/csrf").body());
        HttpResponse<String> jsonLogout =
                HttpClient.newBuilder()
                        .cookieHandler(cookies)
                        .followRedirects(HttpClient.Redirect.NEVER)
                        .connectTimeout(Duration.ofSeconds(15))
                        .build()
                        .send(
                                HttpRequest.newBuilder(uri("/logout"))
                                        .header("Accept", "application/json")
                                        .header(csrf2.get("headerName").asText(), csrf2.get("token").asText())
                                        .POST(HttpRequest.BodyPublishers.noBody())
                                        .build(),
                                HttpResponse.BodyHandlers.ofString());
        assertThat(jsonLogout.statusCode()).isEqualTo(204);
        assertThat(meStatus(client)).isEqualTo(401);
    }

    private void followLogin(HttpClient client) throws Exception {
        HttpResponse<String> started =
                client.send(
                        HttpRequest.newBuilder(uri("/oauth2/authorization/actionfinance")).GET().build(),
                        HttpResponse.BodyHandlers.ofString());
        assertThat(started.statusCode()).isLessThan(500);
        HttpResponse<String> me = jsonGet(client, "/api/v1/access/me");
        assertThat(me.statusCode()).isIn(200, 401);
        if (me.statusCode() == 401) {
            throw new AssertionError(
                    "OIDC login did not establish a session. Last URL status="
                            + started.statusCode()
                            + " body="
                            + started.body().substring(0, Math.min(400, started.body().length())));
        }
    }

    private JsonNode me(HttpClient client) throws Exception {
        HttpResponse<String> response = jsonGet(client, "/api/v1/access/me");
        assertThat(response.statusCode()).isEqualTo(200);
        return mapper.readTree(response.body());
    }

    private int meStatus(HttpClient client) throws Exception {
        return jsonGet(client, "/api/v1/access/me").statusCode();
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
