package br.com.segsense.application.urlcapture;

import java.net.InetAddress;
import java.net.URI;
import java.net.UnknownHostException;
import java.util.Locale;
import java.util.Set;

public final class PublicUrlParser {

  public static final int MAX_URL_LENGTH = 2048;
  private static final Set<Integer> ALLOWED_PORTS = Set.of(80, 443);

  private PublicUrlParser() {}

  public record Parsed(URI uri, String scheme, String host, int port, boolean httpsPreferred) {}

  public static Parsed parse(String raw) {
    if (raw == null || raw.isBlank()) {
      throw new UrlCaptureRejectedException("INVALID_URL", "Informe um endereço público http ou https.");
    }
    String trimmed = raw.trim();
    if (trimmed.length() > MAX_URL_LENGTH) {
      throw new UrlCaptureRejectedException("INVALID_URL", "Este endereço é longo demais para captura nesta demonstração.");
    }
    URI uri;
    try {
      uri = URI.create(trimmed);
    } catch (IllegalArgumentException invalid) {
      throw new UrlCaptureRejectedException("INVALID_URL", "Este endereço não pôde ser lido.");
    }
    if (uri.getScheme() == null) {
      throw new UrlCaptureRejectedException("INVALID_URL", "Use um endereço http ou https público.");
    }
    String scheme = uri.getScheme().toLowerCase(Locale.ROOT);
    if (!"http".equals(scheme) && !"https".equals(scheme)) {
      throw new UrlCaptureRejectedException("INVALID_URL", "Somente endereços http ou https públicos são aceitos.");
    }
    if (uri.getUserInfo() != null && !uri.getUserInfo().isBlank()) {
      throw new UrlCaptureRejectedException("INVALID_URL", "Não use credencial dentro do endereço.");
    }
    String host = uri.getHost();
    if (host == null || host.isBlank()) {
      host = hostFromAuthority(uri.getRawAuthority());
    }
    if (host == null || host.isBlank()) {
      throw new UrlCaptureRejectedException("INVALID_URL", "Este endereço não tem um host público utilizável.");
    }
    host = stripIpv6Brackets(host.toLowerCase(Locale.ROOT));
    if (PublicAddressClassifier.isBlockedHostname(host) || isBlockedIpLiteral(host)) {
      throw new UrlCaptureRejectedException(
          "DNS_BLOCKED", "Este endereço não é uma página pública utilizável nesta demonstração.");
    }
    int port = uri.getPort() == -1 ? ("https".equals(scheme) ? 443 : 80) : uri.getPort();
    if (!ALLOWED_PORTS.contains(port)) {
      throw new UrlCaptureRejectedException("INVALID_URL", "Este endereço usa uma porta que não é permitida na captura.");
    }
    URI sanitized;
    try {
      sanitized =
          URI.create(
              scheme + "://" + literalHost(host) + (needsPort(scheme, port) ? ":" + port : "") + pathAndQuery(uri));
    } catch (IllegalArgumentException invalid) {
      throw new UrlCaptureRejectedException("INVALID_URL", "Este endereço não pôde ser lido.");
    }
    return new Parsed(sanitized, scheme, host, port, "https".equals(scheme));
  }

  static String pathAndQuery(URI uri) {
    String path = uri.getRawPath() == null || uri.getRawPath().isBlank() ? "/" : uri.getRawPath();
    String query = uri.getRawQuery() == null ? "" : "?" + uri.getRawQuery();
    return path + query;
  }

  private static boolean needsPort(String scheme, int port) {
    return ("http".equals(scheme) && port != 80) || ("https".equals(scheme) && port != 443);
  }

  private static String stripIpv6Brackets(String host) {
    if (host.startsWith("[") && host.endsWith("]") && host.length() > 2) {
      return host.substring(1, host.length() - 1);
    }
    return host;
  }

  private static String hostFromAuthority(String authority) {
    if (authority == null || authority.isBlank()) {
      return null;
    }
    String value = authority;
    int at = value.lastIndexOf('@');
    if (at >= 0) {
      value = value.substring(at + 1);
    }
    if (value.startsWith("[")) {
      int end = value.indexOf(']');
      if (end > 1) {
        return value.substring(1, end);
      }
    }
    int colon = value.lastIndexOf(':');
    if (colon > 0 && value.indexOf(':') == colon) {
      return value.substring(0, colon);
    }
    return value;
  }

  private static boolean isBlockedIpLiteral(String host) {
    if (!host.contains(":") && !host.chars().allMatch(ch -> Character.isDigit(ch) || ch == '.')) {
      return false;
    }
    try {
      return PublicAddressClassifier.isBlocked(InetAddress.getByName(host));
    } catch (UnknownHostException ignored) {
      return true;
    }
  }

  private static String literalHost(String host) {
    if (host.contains(":")) {
      return "[" + host + "]";
    }
    return host;
  }
}
