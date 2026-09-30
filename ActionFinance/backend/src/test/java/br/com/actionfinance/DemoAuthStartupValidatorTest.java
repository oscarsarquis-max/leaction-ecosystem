package br.com.actionfinance;

import br.com.actionfinance.configuration.ActionFinanceProperties;
import br.com.actionfinance.infrastructure.security.DemoAuthStartupValidator;
import org.junit.jupiter.api.Test;
import org.springframework.mock.env.MockEnvironment;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class DemoAuthStartupValidatorTest {

    @Test
    void disabledDemoDoesNotRequireTokens() {
        ActionFinanceProperties properties = new ActionFinanceProperties();
        properties.getDemoAuth().setEnabled(false);
        MockEnvironment environment = new MockEnvironment();
        environment.setProperty("server.address", "0.0.0.0");
        assertThatCode(() -> new DemoAuthStartupValidator(properties, environment)).doesNotThrowAnyException();
    }

    @Test
    void enabledDemoWithMissingOrDuplicateTokensFails() {
        ActionFinanceProperties missing = new ActionFinanceProperties();
        missing.getDemoAuth().setEnabled(true);
        assertThatThrownBy(() -> new DemoAuthStartupValidator(missing, loopbackEnv()))
                .isInstanceOf(IllegalStateException.class);

        ActionFinanceProperties duplicate = validTokens();
        duplicate.getDemoAuth().setViewerAToken(duplicate.getDemoAuth().getOperatorAToken());
        assertThatThrownBy(() -> new DemoAuthStartupValidator(duplicate, loopbackEnv()))
                .isInstanceOf(IllegalStateException.class);
    }

    @Test
    void enabledDemoRejectsMissingOrPublicBind() {
        ActionFinanceProperties properties = validTokens();
        assertThatThrownBy(() -> new DemoAuthStartupValidator(properties, new MockEnvironment()))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("loopback");
        assertThatThrownBy(() -> new DemoAuthStartupValidator(properties, env("server.address", "0.0.0.0")))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("public bind");
        assertThatThrownBy(() -> new DemoAuthStartupValidator(properties, env("server.address", "::")))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("public bind");
        assertThatThrownBy(() -> new DemoAuthStartupValidator(properties, env("server.address", "192.168.1.10")))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("public bind");
        MockEnvironment management = loopbackEnv();
        management.setProperty("management.server.address", "0.0.0.0");
        assertThatThrownBy(() -> new DemoAuthStartupValidator(properties, management))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("management.server.address");
    }

    @Test
    void enabledDemoAcceptsLoopbackAndRejectsEnvironmentOverride() {
        ActionFinanceProperties properties = validTokens();
        assertThatCode(() -> new DemoAuthStartupValidator(properties, loopbackEnv())).doesNotThrowAnyException();
        MockEnvironment ipv6 = env("server.address", "::1");
        ipv6.setProperty("management.server.address", "127.0.0.1");
        assertThatCode(() -> new DemoAuthStartupValidator(properties, ipv6)).doesNotThrowAnyException();
        assertThatThrownBy(() -> new DemoAuthStartupValidator(properties, env("SERVER_ADDRESS", "0.0.0.0")))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("public bind");
    }

    private static ActionFinanceProperties validTokens() {
        ActionFinanceProperties properties = new ActionFinanceProperties();
        properties.getDemoAuth().setEnabled(true);
        properties.getDemoAuth().setOperatorAToken("operator-demo-token-aaaaaaaaaaaaaaaaaaaa");
        properties.getDemoAuth().setViewerAToken("viewer-a-demo-token-bbbbbbbbbbbbbbbbbbbb");
        properties.getDemoAuth().setViewerBToken("viewer-b-demo-token-cccccccccccccccccccc");
        return properties;
    }

    private static MockEnvironment loopbackEnv() {
        return env("server.address", "127.0.0.1");
    }

    private static MockEnvironment env(String key, String value) {
        MockEnvironment environment = new MockEnvironment();
        environment.setProperty(key, value);
        return environment;
    }
}
