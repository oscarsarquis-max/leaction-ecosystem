package br.com.actionfinance.infrastructure.security;

import br.com.actionfinance.configuration.ActionFinanceProperties;
import org.springframework.context.annotation.Profile;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.util.Arrays;
import java.util.List;

@Component
@Profile("production")
public class ProductionSafetyValidator {

    public ProductionSafetyValidator(ActionFinanceProperties properties, Environment environment) {
        List<String> profiles = Arrays.asList(environment.getActiveProfiles());
        if (profiles.contains("local-demo") || profiles.contains("oidc-it")) {
            throw new IllegalStateException("Production cannot be combined with a test or demo profile.");
        }
        if (properties.getDemoAuth().isEnabled()) {
            throw new IllegalStateException("Production profile cannot enable demo authentication.");
        }
        ActionFinanceProperties.Oidc oidc = properties.getOidc();
        if (!oidc.isEnabled()) {
            throw new IllegalStateException("Production requires actionfinance.oidc.enabled=true.");
        }
        requirePresent(oidc.getClientId(), "ACTIONFINANCE_OIDC_CLIENT_ID");
        requirePresent(oidc.getClientSecret(), "ACTIONFINANCE_OIDC_CLIENT_SECRET");
        URI origin = ProductionPublicUris.requireHttpsOrigin(properties.getPublicOrigin(), "ACTIONFINANCE_PUBLIC_ORIGIN");
        ProductionPublicUris.requireHttpsAbsolute(oidc.getIssuer(), "ACTIONFINANCE_OIDC_ISSUER");
        String registrationId =
                properties.getLoginRegistrationId() == null || properties.getLoginRegistrationId().isBlank()
                        ? "actionfinance"
                        : properties.getLoginRegistrationId().trim();
        ProductionPublicUris.requireOidcCallback(oidc.getRedirectUri(), origin, registrationId);
        if (!properties.getSession().isCookieSecure()) {
            throw new IllegalStateException("Production requires a Secure session cookie.");
        }
        String servletSecure = environment.getProperty("server.servlet.session.cookie.secure");
        if (servletSecure != null && !Boolean.parseBoolean(servletSecure)) {
            throw new IllegalStateException("Production servlet session cookie must be Secure.");
        }
        if (properties.getIngress().isTrustForwardedHeaders()) {
            throw new IllegalStateException(
                    "Production does not trust forwarded headers when the process may also be reached directly. Keep ACTIONFINANCE_TRUST_FORWARDED_HEADERS=false and expose the service only through the authorized ingress.");
        }
        String forwarded = environment.getProperty("server.forward-headers-strategy", "none");
        if (!"none".equalsIgnoreCase(forwarded)) {
            throw new IllegalStateException(
                    "Production must set server.forward-headers-strategy=none so client-supplied Host or X-Forwarded-* headers cannot change origin or callback.");
        }
    }

    private static void requirePresent(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalStateException("Missing required production setting " + name + ".");
        }
    }
}
