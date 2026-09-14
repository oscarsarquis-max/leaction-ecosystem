package br.com.segsense.application.demo;

import br.com.segsense.domain.demo.DemoProtectionException;
import java.net.URI;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.Set;

public final class DemoContextUrlGuard {

  private static final Set<String> HOSTS = Set.of("127.0.0.1", "localhost");
  private static final String PATH_PREFIX = "/demonstracao/fontes/";
  private static final Set<Integer> DEFAULT_PORTS = Set.of(5178);

  private DemoContextUrlGuard() {}

  public record Accepted(String path, String referenceUrl, int port, String host) {}

  public static String normalizeOrReject(String raw) {
    return accept(raw, DEFAULT_PORTS).path();
  }

  public static Accepted accept(String raw, Set<Integer> allowedPorts) {
    if (raw == null || raw.isBlank()) {
      throw new DemoProtectionException("INVALID_CONTEXT_URL", 400, "Informe um link governado desta demonstração.");
    }
    String trimmed = raw.trim();
    if (trimmed.length() > 200) {
      throw new DemoProtectionException("INVALID_CONTEXT_URL", 400, "O link informado não é uma fonte governada.");
    }
    URI uri;
    try {
      uri = URI.create(trimmed);
    } catch (IllegalArgumentException invalid) {
      throw new DemoProtectionException("INVALID_CONTEXT_URL", 400, "O link informado não é uma fonte governada.");
    }
    if (uri.getScheme() == null || !"http".equalsIgnoreCase(uri.getScheme())) {
      throw new DemoProtectionException("INVALID_CONTEXT_URL", 400, "Somente links http locais governados são aceitos nesta fatia.");
    }
    if (uri.getUserInfo() != null) {
      throw new DemoProtectionException("INVALID_CONTEXT_URL", 400, "O link informado não é uma fonte governada.");
    }
    String host = uri.getHost() == null ? "" : uri.getHost().toLowerCase(Locale.ROOT);
    if (!HOSTS.contains(host)) {
      throw new DemoProtectionException("INVALID_CONTEXT_URL", 400, "O link não está no registro de fontes governadas desta demonstração.");
    }
    int port = uri.getPort() == -1 ? 80 : uri.getPort();
    Set<Integer> ports = allowedPorts == null || allowedPorts.isEmpty() ? DEFAULT_PORTS : allowedPorts;
    if (!ports.contains(port)) {
      throw new DemoProtectionException("INVALID_CONTEXT_URL", 400, "O link não está no registro de fontes governadas desta demonstração.");
    }
    if (uri.getQuery() != null || uri.getFragment() != null) {
      throw new DemoProtectionException("INVALID_CONTEXT_URL", 400, "O link informado não é uma fonte governada.");
    }
    String path = uri.getPath() == null ? "" : uri.getPath();
    if (path.endsWith("/") && path.length() > 1) {
      path = path.substring(0, path.length() - 1);
    }
    if (!path.startsWith(PATH_PREFIX) || path.equals(PATH_PREFIX)) {
      throw new DemoProtectionException("INVALID_CONTEXT_URL", 400, "O link não está no registro de fontes governadas desta demonstração.");
    }
    String slug = path.substring(PATH_PREFIX.length());
    if (slug.contains("/") || slug.contains("..") || slug.contains("%")) {
      throw new DemoProtectionException("INVALID_CONTEXT_URL", 400, "O link não está no registro de fontes governadas desta demonstração.");
    }
    String normalizedPath = PATH_PREFIX + slug;
    return new Accepted(normalizedPath(normalizedPath), "http://" + host + ":" + port + normalizedPath, port, host);
  }

  private static String normalizedPath(String path) {
    return path;
  }

  public static Optional<String> slugOf(String normalizedPath) {
    if (normalizedPath == null || !normalizedPath.startsWith(PATH_PREFIX)) {
      return Optional.empty();
    }
    return Optional.of(normalizedPath.substring(PATH_PREFIX.length()));
  }

  public static List<String> allowedHosts() {
    return List.of("127.0.0.1", "localhost");
  }
}
