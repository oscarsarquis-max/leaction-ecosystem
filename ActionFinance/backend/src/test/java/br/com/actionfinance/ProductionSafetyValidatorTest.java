package br.com.actionfinance;

import br.com.actionfinance.configuration.ActionFinanceProperties;
import br.com.actionfinance.infrastructure.security.ProductionSafetyValidator;
import org.junit.jupiter.api.Test;
import org.springframework.mock.env.MockEnvironment;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ProductionSafetyValidatorTest {

    @Test
    void rejectsProductionCombinedWithDemo() {
        ActionFinanceProperties properties = validProduction();
        properties.getDemoAuth().setEnabled(true);
        MockEnvironment environment = productionEnv();
        assertThatThrownBy(() -> new ProductionSafetyValidator(properties, environment))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("demo");
    }

    @Test
    void rejectsProductionCombinedWithOidcItProfile() {
        ActionFinanceProperties properties = validProduction();
        MockEnvironment environment = new MockEnvironment();
        environment.setActiveProfiles("production", "oidc-it");
        environment.setProperty("server.forward-headers-strategy", "none");
        environment.setProperty("server.servlet.session.cookie.secure", "true");
        assertThatThrownBy(() -> new ProductionSafetyValidator(properties, environment))
                .hasMessageContaining("test or demo profile");
    }

    @Test
    void rejectsHttpCallbackAndInsecureCookie() {
        ActionFinanceProperties properties = validProduction();
        properties.getOidc().setRedirectUri("http://actionfinance.example/login/oauth2/code/actionfinance");
        assertThatThrownBy(() -> new ProductionSafetyValidator(properties, productionEnv()))
                .hasMessageContaining("HTTPS");
        ActionFinanceProperties insecureCookie = validProduction();
        insecureCookie.getSession().setCookieSecure(false);
        assertThatThrownBy(() -> new ProductionSafetyValidator(insecureCookie, productionEnv()))
                .hasMessageContaining("Secure");
    }

    @Test
    void rejectsTrustingForwardedHeaders() {
        ActionFinanceProperties properties = validProduction();
        properties.getIngress().setTrustForwardedHeaders(true);
        assertThatThrownBy(() -> new ProductionSafetyValidator(properties, productionEnv()))
                .hasMessageContaining("forwarded");
    }

    @Test
    void rejectsMissingIssuerWithoutPrintingSecret() {
        ActionFinanceProperties properties = validProduction();
        properties.getOidc().setIssuer("");
        properties.getOidc().setClientSecret("super-secret-value-should-not-appear");
        assertThatThrownBy(() -> new ProductionSafetyValidator(properties, productionEnv()))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("ACTIONFINANCE_OIDC_ISSUER")
                .hasMessageNotContaining("super-secret-value-should-not-appear");
    }

    @Test
    void acceptsStrictHttpsProduction() {
        assertThatCode(() -> new ProductionSafetyValidator(validProduction(), productionEnv()))
                .doesNotThrowAnyException();
    }

    private static MockEnvironment productionEnv() {
        MockEnvironment environment = new MockEnvironment();
        environment.setActiveProfiles("production");
        environment.setProperty("server.forward-headers-strategy", "none");
        environment.setProperty("server.servlet.session.cookie.secure", "true");
        return environment;
    }

    private static ActionFinanceProperties validProduction() {
        ActionFinanceProperties properties = new ActionFinanceProperties();
        properties.getOidc().setEnabled(true);
        properties.getOidc().setIssuer("https://idp.example/realms/actionfinance");
        properties.getOidc().setClientId("actionfinance");
        properties.getOidc().setClientSecret("secret");
        properties.getOidc().setRedirectUri("https://actionfinance.actionhub.com.br/login/oauth2/code/actionfinance");
        properties.setPublicOrigin("https://actionfinance.actionhub.com.br");
        properties.getSession().setCookieSecure(true);
        return properties;
    }
}
