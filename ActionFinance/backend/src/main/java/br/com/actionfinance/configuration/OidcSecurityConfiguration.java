package br.com.actionfinance.configuration;

import br.com.actionfinance.application.identity.IdentityAuthorizationService;
import br.com.actionfinance.infrastructure.security.AuthorizationRefreshFilter;
import br.com.actionfinance.infrastructure.security.OidcLoginFailureHandler;
import br.com.actionfinance.infrastructure.security.OidcLoginSuccessHandler;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.web.authentication.AuthenticationFailureHandler;
import org.springframework.security.web.authentication.AuthenticationSuccessHandler;

@Configuration
@ConditionalOnProperty(name = "actionfinance.oidc.enabled", havingValue = "true")
public class OidcSecurityConfiguration {

    @Bean
    AuthenticationSuccessHandler oidcLoginSuccessHandler(
            IdentityAuthorizationService identities, ActionFinanceProperties properties) {
        return new OidcLoginSuccessHandler(identities, properties);
    }

    @Bean
    AuthenticationFailureHandler oidcLoginFailureHandler(ActionFinanceProperties properties) {
        return new OidcLoginFailureHandler(properties);
    }

    @Bean
    AuthorizationRefreshFilter authorizationRefreshFilter(IdentityAuthorizationService identities) {
        return new AuthorizationRefreshFilter(identities);
    }
}
