package br.com.banco.spider.contextuallink.domain;

import java.net.InetAddress;
import java.net.URI;
import java.net.UnknownHostException;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * Allowlist explícita para fetch contextual. Não é um cliente HTTP genérico (anti-SSRF).
 */
public final class AcquisitionUrlGuard {

  public static final class BlockedAcquisitionException extends RuntimeException {
    public BlockedAcquisitionException(String reason) {
      super(reason);
    }
  }

  private static final Set<String> BLOCKED_HOSTS =
      Set.of(
          "169.254.169.254",
          "metadata.google.internal",
          "metadata.goog",
          "instance-data");

  private final List<String> allowedOrigins;
  private final List<String> allowedPathPrefixes;

  public AcquisitionUrlGuard(List<String> allowedOrigins, List<String> allowedPathPrefixes) {
    this.allowedOrigins = allowedOrigins == null ? List.of() : List.copyOf(allowedOrigins);
    this.allowedPathPrefixes =
        allowedPathPrefixes == null ? List.of() : List.copyOf(allowedPathPrefixes);
  }

  public URI validate(String rawUrl) {
    if (rawUrl == null || rawUrl.isBlank()) {
      throw new BlockedAcquisitionException("empty_url");
    }
    URI uri;
    try {
      uri = URI.create(rawUrl.trim()).normalize();
    } catch (IllegalArgumentException ex) {
      throw new BlockedAcquisitionException("malformed_url");
    }
    if (uri.getScheme() == null) {
      throw new BlockedAcquisitionException("scheme_not_allowed");
    }
    String scheme = uri.getScheme().toLowerCase(Locale.ROOT);
    if (!scheme.equals("http") && !scheme.equals("https")) {
      throw new BlockedAcquisitionException("scheme_not_allowed");
    }
    if (uri.getHost() == null) {
      throw new BlockedAcquisitionException("missing_host");
    }
    if (uri.getUserInfo() != null) {
      throw new BlockedAcquisitionException("userinfo_not_allowed");
    }
    String host = uri.getHost().toLowerCase(Locale.ROOT);
    if (BLOCKED_HOSTS.contains(host) || host.endsWith(".internal")) {
      throw new BlockedAcquisitionException("metadata_blocked");
    }
    String origin = originOf(uri);
    if (allowedOrigins.stream().noneMatch(allowed -> originsMatch(allowed, origin))) {
      throw new BlockedAcquisitionException("origin_not_allowlisted");
    }
    String path = uri.getPath() == null || uri.getPath().isBlank() ? "/" : uri.getPath();
    if (path.contains("..")) {
      throw new BlockedAcquisitionException("path_traversal");
    }
    if (allowedPathPrefixes.stream().noneMatch(path::startsWith)) {
      throw new BlockedAcquisitionException("path_not_allowlisted");
    }
    assertResolvedAddressSafe(host, origin);
    return uri;
  }

  public URI validateRedirect(URI current, String location) {
    if (location == null || location.isBlank()) {
      throw new BlockedAcquisitionException("empty_redirect");
    }
    URI next = current.resolve(location).normalize();
    return validate(next.toString());
  }

  private void assertResolvedAddressSafe(String host, String origin) {
    try {
      for (InetAddress address : InetAddress.getAllByName(host)) {
        if (isMetadataAddress(address)) {
          throw new BlockedAcquisitionException("metadata_ip_blocked");
        }
        boolean loopbackOrPrivate =
            address.isLoopbackAddress()
                || address.isLinkLocalAddress()
                || address.isSiteLocalAddress()
                || address.isAnyLocalAddress();
        if (loopbackOrPrivate && !isAllowlistedLoopback(origin)) {
          throw new BlockedAcquisitionException("private_network_blocked");
        }
      }
    } catch (UnknownHostException ex) {
      throw new BlockedAcquisitionException("unresolvable_host");
    }
  }

  private boolean isAllowlistedLoopback(String origin) {
    return allowedOrigins.stream().anyMatch(allowed -> originsMatch(allowed, origin));
  }

  private static boolean isMetadataAddress(InetAddress address) {
    byte[] bytes = address.getAddress();
    if (bytes.length == 4
        && (bytes[0] & 0xFF) == 169
        && (bytes[1] & 0xFF) == 254
        && (bytes[2] & 0xFF) == 169
        && (bytes[3] & 0xFF) == 254) {
      return true;
    }
    return "169.254.169.254".equals(address.getHostAddress());
  }

  private static boolean originsMatch(String allowed, String actual) {
    return normalizeOrigin(allowed).equals(normalizeOrigin(actual));
  }

  private static String originOf(URI uri) {
    int port = uri.getPort();
    String host = uri.getHost().toLowerCase(Locale.ROOT);
    String scheme = uri.getScheme().toLowerCase(Locale.ROOT);
    if (port < 0) {
      return scheme + "://" + host;
    }
    return scheme + "://" + host + ":" + port;
  }

  private static String normalizeOrigin(String origin) {
    URI uri = URI.create(origin);
    String scheme = uri.getScheme().toLowerCase(Locale.ROOT);
    String host = uri.getHost().toLowerCase(Locale.ROOT);
    int port = uri.getPort();
    if (port < 0) {
      port = scheme.equals("https") ? 443 : 80;
    }
    boolean defaultPort =
        (scheme.equals("http") && port == 80) || (scheme.equals("https") && port == 443);
    if (defaultPort) {
      return scheme + "://" + host;
    }
    return scheme + "://" + host + ":" + port;
  }
}
