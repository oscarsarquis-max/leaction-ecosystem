package br.com.segsense.infrastructure.link;

import br.com.segsense.application.link.LinkTtlSettings;
import br.com.segsense.application.link.PublicContextUrl;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.Arrays;
import java.util.Locale;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;

@Configuration
public class ContextLinkConfiguration {

  private static final Set<String> RELAXED_PROFILES = Set.of("local", "test");

  @Bean
  LinkTtlSettings linkTtlSettings(
      @Value("${segsense.link.max-ttl-days:30}") int maxTtlDays,
      @Value("${segsense.link.absolute-max-ttl-days:90}") int absoluteMaxTtlDays) {
    int absolute = Math.min(absoluteMaxTtlDays, 90);
    int max = Math.min(maxTtlDays, absolute);
    return new LinkTtlSettings(max, absolute);
  }

  @Bean
  PublicContextUrl publicContextUrl(
      @Value("${segsense.public.base-url}") String configuredBaseUrl, Environment environment) {
    String normalized = normalize(configuredBaseUrl, environment);
    return new ConfiguredPublicContextUrl(normalized);
  }

  static String normalize(String raw, Environment environment) {
    if (raw == null || raw.isBlank()) {
      throw new IllegalStateException("SEGSENSE_PUBLIC_BASE_URL is required");
    }
    URI uri;
    try {
      uri = new URI(raw.trim());
    } catch (URISyntaxException exception) {
      throw new IllegalStateException("SEGSENSE_PUBLIC_BASE_URL is invalid");
    }
    if (uri.getScheme() == null || uri.getHost() == null || uri.getHost().isBlank()) {
      throw new IllegalStateException("SEGSENSE_PUBLIC_BASE_URL is invalid");
    }
    if (uri.getUserInfo() != null || uri.getFragment() != null || uri.getRawQuery() != null) {
      throw new IllegalStateException("SEGSENSE_PUBLIC_BASE_URL is invalid");
    }
    String path = uri.getPath();
    if (path != null && !path.isBlank() && !"/".equals(path)) {
      throw new IllegalStateException("SEGSENSE_PUBLIC_BASE_URL must not include an unexpected path");
    }
    boolean https = "https".equalsIgnoreCase(uri.getScheme());
    boolean http = "http".equalsIgnoreCase(uri.getScheme());
    if (!https && !http) {
      throw new IllegalStateException("SEGSENSE_PUBLIC_BASE_URL scheme is invalid");
    }
    if (!https && !relaxed(environment)) {
      throw new IllegalStateException("SEGSENSE_PUBLIC_BASE_URL must use https outside local/test");
    }
    if (!https && !isLoopback(uri.getHost())) {
      throw new IllegalStateException("HTTP public base URL is allowed only for loopback hosts");
    }
    int port = uri.getPort();
    String authority = uri.getHost().toLowerCase(Locale.ROOT);
    if (port > 0 && port != defaultPort(uri.getScheme())) {
      authority = authority + ":" + port;
    }
    return uri.getScheme().toLowerCase(Locale.ROOT) + "://" + authority;
  }

  private static boolean relaxed(Environment environment) {
    String[] profiles = environment.getActiveProfiles();
    if (profiles == null || profiles.length == 0) {
      return false;
    }
    return Arrays.stream(profiles)
        .map(profile -> profile.toLowerCase(Locale.ROOT))
        .allMatch(RELAXED_PROFILES::contains);
  }

  private static boolean isLoopback(String host) {
    String normalized = host.toLowerCase(Locale.ROOT);
    return "127.0.0.1".equals(normalized)
        || "localhost".equals(normalized)
        || "[::1]".equals(normalized)
        || "::1".equals(normalized);
  }

  private static int defaultPort(String scheme) {
    return "https".equalsIgnoreCase(scheme) ? 443 : 80;
  }

  static final class ConfiguredPublicContextUrl implements PublicContextUrl {
    private final String baseUrl;

    ConfiguredPublicContextUrl(String configuredBaseUrl) {
      this.baseUrl = configuredBaseUrl;
    }

    @Override
    public String publicUrl(String opaqueToken) {
      return baseUrl + "/c/" + opaqueToken;
    }

    @Override
    public String configuredBaseUrl() {
      return baseUrl;
    }
  }
}
