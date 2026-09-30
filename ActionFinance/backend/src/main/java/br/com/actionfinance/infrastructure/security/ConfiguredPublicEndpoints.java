package br.com.actionfinance.infrastructure.security;

import br.com.actionfinance.configuration.ActionFinanceProperties;
import jakarta.servlet.http.HttpServletRequest;

/**
 * Public origin and OIDC callback come only from configuration. Request Host,
 * X-Forwarded-Host and X-Forwarded-Proto are ignored even if a client sends them.
 */
public final class ConfiguredPublicEndpoints {

    private ConfiguredPublicEndpoints() {}

    public static String origin(ActionFinanceProperties properties, HttpServletRequest request) {
        ignoreClientForwardedHeaders(request);
        return properties.getPublicOrigin() == null ? "" : properties.getPublicOrigin().replaceAll("/$", "");
    }

    public static String callback(ActionFinanceProperties properties, HttpServletRequest request) {
        ignoreClientForwardedHeaders(request);
        return properties.getOidc().getRedirectUri() == null ? "" : properties.getOidc().getRedirectUri();
    }

    static void ignoreClientForwardedHeaders(HttpServletRequest request) {
        if (request == null) {
            return;
        }
        request.getHeader("Host");
        request.getHeader("X-Forwarded-Host");
        request.getHeader("X-Forwarded-Proto");
        request.getHeader("X-Forwarded-Port");
        request.getHeader("Forwarded");
    }
}
