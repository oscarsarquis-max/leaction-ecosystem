package br.com.actionfinance.infrastructure.security;

import java.net.URI;
import java.util.Locale;

public final class ProductionPublicUris {

    public static final String OIDC_CALLBACK_PATH = "/login/oauth2/code/actionfinance";

    private ProductionPublicUris() {}

    public static URI requireHttpsOrigin(String value, String name) {
        URI uri = parse(value, name);
        requireHttps(uri, name);
        requireNoUserInfo(uri, name);
        requireNoFragment(uri, name);
        requireValidHost(uri, name);
        if (uri.getQuery() != null && !uri.getQuery().isBlank()) {
            throw new IllegalStateException(name + " must be an origin without query.");
        }
        String path = uri.getRawPath();
        if (path != null && !path.isBlank() && !"/".equals(path)) {
            throw new IllegalStateException(name + " must be an origin without an application path.");
        }
        return uri;
    }

    public static URI requireHttpsAbsolute(String value, String name) {
        URI uri = parse(value, name);
        requireHttps(uri, name);
        requireNoUserInfo(uri, name);
        requireNoFragment(uri, name);
        requireValidHost(uri, name);
        return uri;
    }

    public static URI requireOidcCallback(String value, URI publicOrigin, String registrationId) {
        URI callback = requireHttpsAbsolute(value, "ACTIONFINANCE_OIDC_REDIRECT_URI");
        if (!sameOrigin(publicOrigin, callback)) {
            throw new IllegalStateException("OIDC callback must belong to the configured public origin.");
        }
        String expectedPath = "/login/oauth2/code/" + registrationId;
        String path = callback.getRawPath() == null ? "" : callback.getRawPath();
        if (!expectedPath.equals(path)) {
            throw new IllegalStateException("OIDC callback must use the registered route " + expectedPath + ".");
        }
        if (callback.getQuery() != null && !callback.getQuery().isBlank()) {
            throw new IllegalStateException("OIDC callback must not include a query string.");
        }
        return callback;
    }

    public static String configuredOrigin(String publicOrigin) {
        return requireHttpsOrigin(publicOrigin, "ACTIONFINANCE_PUBLIC_ORIGIN").toString().replaceAll("/$", "");
    }

    public static boolean sameOrigin(URI left, URI right) {
        return scheme(left).equals(scheme(right))
                && host(left).equals(host(right))
                && port(left) == port(right);
    }

    private static URI parse(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalStateException("Missing required production setting " + name + ".");
        }
        URI uri;
        try {
            uri = URI.create(value.trim());
        } catch (IllegalArgumentException ex) {
            throw new IllegalStateException(name + " is not a valid URI.");
        }
        if (!uri.isAbsolute() || uri.getScheme() == null) {
            throw new IllegalStateException(name + " must be an absolute URI.");
        }
        return uri;
    }

    private static void requireHttps(URI uri, String name) {
        if (!"https".equalsIgnoreCase(uri.getScheme())) {
            throw new IllegalStateException(name + " must use HTTPS.");
        }
    }

    private static void requireNoUserInfo(URI uri, String name) {
        if (uri.getRawUserInfo() != null && !uri.getRawUserInfo().isBlank()) {
            throw new IllegalStateException(name + " must not include userinfo.");
        }
    }

    private static void requireNoFragment(URI uri, String name) {
        if (uri.getRawFragment() != null && !uri.getRawFragment().isBlank()) {
            throw new IllegalStateException(name + " must not include a fragment.");
        }
    }

    private static void requireValidHost(URI uri, String name) {
        String host = uri.getHost();
        if (host == null || host.isBlank()) {
            throw new IllegalStateException(name + " must include a valid host.");
        }
        if (host.contains(" ") || host.startsWith(".") || host.endsWith(".")) {
            throw new IllegalStateException(name + " host is invalid.");
        }
    }

    private static String scheme(URI uri) {
        return uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.ROOT);
    }

    private static String host(URI uri) {
        return uri.getHost() == null ? "" : uri.getHost().toLowerCase(Locale.ROOT);
    }

    private static int port(URI uri) {
        if (uri.getPort() != -1) {
            return uri.getPort();
        }
        return "https".equalsIgnoreCase(uri.getScheme()) ? 443 : 80;
    }
}
