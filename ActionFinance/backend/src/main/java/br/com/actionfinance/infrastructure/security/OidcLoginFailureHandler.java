package br.com.actionfinance.infrastructure.security;

import br.com.actionfinance.configuration.ActionFinanceProperties;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.authentication.AuthenticationFailureHandler;

import java.io.IOException;

public class OidcLoginFailureHandler implements AuthenticationFailureHandler {

    private static final Logger log = LoggerFactory.getLogger(OidcLoginFailureHandler.class);

    private final ActionFinanceProperties properties;

    public OidcLoginFailureHandler(ActionFinanceProperties properties) {
        this.properties = properties;
    }

    @Override
    public void onAuthenticationFailure(
            HttpServletRequest request, HttpServletResponse response, AuthenticationException exception)
            throws IOException {
        if (exception instanceof org.springframework.security.oauth2.core.OAuth2AuthenticationException oauth) {
            log.warn(
                    "OIDC login failed: error={} description={}",
                    oauth.getError().getErrorCode(),
                    oauth.getError().getDescription());
        } else {
            log.warn("OIDC login failed: {}", exception.toString());
        }
        response.sendRedirect(properties.getPublicOrigin().replaceAll("/$", "") + "/?login=failed");
    }
}
