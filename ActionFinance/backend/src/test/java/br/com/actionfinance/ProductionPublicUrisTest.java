package br.com.actionfinance;

import br.com.actionfinance.configuration.ActionFinanceProperties;
import br.com.actionfinance.infrastructure.security.ConfiguredPublicEndpoints;
import br.com.actionfinance.infrastructure.security.ProductionPublicUris;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

import java.net.URI;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ProductionPublicUrisTest {

    @Test
    void rejectsHttpHostSpoofUserinfoAndForeignCallback() {
        assertThatThrownBy(() -> ProductionPublicUris.requireHttpsOrigin("http://actionfinance.example", "ORIGIN"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("HTTPS");
        assertThatThrownBy(
                        () ->
                                ProductionPublicUris.requireHttpsOrigin(
                                        "http://127.0.0.1.evil.example", "ORIGIN"))
                .hasMessageContaining("HTTPS");
        URI spoofed = ProductionPublicUris.requireHttpsOrigin("https://127.0.0.1.evil.example", "ORIGIN");
        assertThat(spoofed.getHost()).isEqualTo("127.0.0.1.evil.example");
        assertThatThrownBy(
                        () ->
                                ProductionPublicUris.requireHttpsOrigin(
                                        "https://user:pass@finance.example", "ORIGIN"))
                .hasMessageContaining("userinfo");
        URI origin = ProductionPublicUris.requireHttpsOrigin("https://finance.example", "ORIGIN");
        assertThatThrownBy(
                        () ->
                                ProductionPublicUris.requireOidcCallback(
                                        "https://other.example/login/oauth2/code/actionfinance",
                                        origin,
                                        "actionfinance"))
                .hasMessageContaining("public origin");
        assertThatThrownBy(
                        () ->
                                ProductionPublicUris.requireOidcCallback(
                                        "https://finance.example/callback", origin, "actionfinance"))
                .hasMessageContaining("registered route");
    }

    @Test
    void clientForwardedHeadersDoNotChangeConfiguredOriginOrCallback() {
        ActionFinanceProperties properties = new ActionFinanceProperties();
        properties.setPublicOrigin("https://actionfinance.example");
        properties.getOidc().setRedirectUri("https://actionfinance.example/login/oauth2/code/actionfinance");
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("Host", "127.0.0.1.evil.example");
        request.addHeader("X-Forwarded-Host", "attacker.example");
        request.addHeader("X-Forwarded-Proto", "http");
        assertThat(ConfiguredPublicEndpoints.origin(properties, request)).isEqualTo("https://actionfinance.example");
        assertThat(ConfiguredPublicEndpoints.callback(properties, request))
                .isEqualTo("https://actionfinance.example/login/oauth2/code/actionfinance");
    }
}
