package br.com.actionfinance.infrastructure.security;

import br.com.actionfinance.configuration.ActionFinanceProperties;

import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.Optional;

public final class CognitoLogoutUrls {

    private CognitoLogoutUrls() {}

    public static Optional<String> providerLogout(ActionFinanceProperties properties) {
        if (properties == null || !properties.getOidc().isEnabled()) {
            return Optional.empty();
        }
        String hosted = trimSlash(properties.getOidc().getHostedUiOrigin());
        String clientId = properties.getOidc().getClientId() == null ? "" : properties.getOidc().getClientId().trim();
        String origin = trimSlash(properties.getPublicOrigin());
        String registration = properties.getLoginRegistrationId() == null || properties.getLoginRegistrationId().isBlank()
                ? "actionfinance"
                : properties.getLoginRegistrationId().trim();
        if (hosted.isEmpty() || clientId.isEmpty() || origin.isEmpty()) {
            return Optional.empty();
        }
        if (!isAllowedHostedOrigin(hosted) || clientId.contains("&") || clientId.contains("/") || clientId.contains("?")) {
            return Optional.empty();
        }
        String logoutUri = origin + "/oauth2/authorization/" + registration;
        if (!logoutUri.startsWith(origin + "/oauth2/authorization/")) {
            return Optional.empty();
        }
        String target = hosted
                + "/logout?client_id="
                + URLEncoder.encode(clientId, StandardCharsets.UTF_8)
                + "&logout_uri="
                + URLEncoder.encode(logoutUri, StandardCharsets.UTF_8);
        return Optional.of(target);
    }

    static boolean isAllowedHostedOrigin(String hosted) {
        URI uri;
        try {
            uri = URI.create(hosted);
        } catch (IllegalArgumentException ex) {
            return false;
        }
        if (!uri.isAbsolute() || uri.getHost() == null || uri.getRawQuery() != null || uri.getRawFragment() != null) {
            return false;
        }
        String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.ROOT);
        String host = uri.getHost().toLowerCase(Locale.ROOT);
        if ("https".equals(scheme) && host.endsWith(".amazoncognito.com")) {
            return true;
        }
        return "http".equals(scheme) && ("127.0.0.1".equals(host) || "localhost".equals(host));
    }

    private static String trimSlash(String value) {
        if (value == null) {
            return "";
        }
        return value.trim().replaceAll("/$", "");
    }
}
