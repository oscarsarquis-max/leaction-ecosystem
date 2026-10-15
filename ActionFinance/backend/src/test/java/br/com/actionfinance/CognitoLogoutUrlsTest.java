package br.com.actionfinance;

import br.com.actionfinance.configuration.ActionFinanceProperties;
import br.com.actionfinance.infrastructure.security.CognitoLogoutUrls;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class CognitoLogoutUrlsTest {

    @Test
    void buildsHostedUiLogoutWithFixedInternalAuthorizationReturn() {
        ActionFinanceProperties properties = finance();
        String target = CognitoLogoutUrls.providerLogout(properties).orElseThrow();
        assertThat(target)
                .isEqualTo(
                        "https://actionfinance-253137917703.auth.us-east-2.amazoncognito.com/logout?client_id=275ig9d7lfi0j7if9rqe374rqc&logout_uri=https%3A%2F%2Factionfinance.actionhub.com.br%2Foauth2%2Fauthorization%2Factionfinance");
    }

    @Test
    void ignoresMissingHostedOriginInsteadOfInventingALoginState() {
        ActionFinanceProperties properties = finance();
        properties.getOidc().setHostedUiOrigin("");
        assertThat(CognitoLogoutUrls.providerLogout(properties)).isEmpty();
    }

    @Test
    void rejectsAHostedOriginOutsideCognito() {
        ActionFinanceProperties properties = finance();
        properties.getOidc().setHostedUiOrigin("https://evil.example/logout");
        assertThat(CognitoLogoutUrls.providerLogout(properties)).isEmpty();
    }

    private static ActionFinanceProperties finance() {
        ActionFinanceProperties properties = new ActionFinanceProperties();
        properties.getOidc().setEnabled(true);
        properties.getOidc().setClientId("275ig9d7lfi0j7if9rqe374rqc");
        properties.getOidc().setHostedUiOrigin("https://actionfinance-253137917703.auth.us-east-2.amazoncognito.com");
        properties.setPublicOrigin("https://actionfinance.actionhub.com.br");
        properties.setLoginRegistrationId("actionfinance");
        return properties;
    }
}
