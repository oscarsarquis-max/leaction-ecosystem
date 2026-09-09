package br.com.banco.spider.contextuallink.domain;

import java.net.URI;
import java.util.Locale;
import java.util.Optional;

public final class ReferrerClassifier {

  private ReferrerClassifier() {}

  public record Classification(
      ReferrerAvailability availability, String referrer, String origin, URI fullUri) {}

  public static Classification classify(String rawReferrer) {
    if (rawReferrer == null || rawReferrer.isBlank()) {
      return new Classification(ReferrerAvailability.REFERRER_UNAVAILABLE, "", "", null);
    }
    String trimmed = rawReferrer.trim();
    URI uri;
    try {
      uri = URI.create(trimmed);
    } catch (IllegalArgumentException ex) {
      return new Classification(ReferrerAvailability.REFERRER_UNAVAILABLE, "", "", null);
    }
    if (uri.getScheme() == null || uri.getHost() == null) {
      return new Classification(ReferrerAvailability.REFERRER_UNAVAILABLE, "", "", null);
    }
    String scheme = uri.getScheme().toLowerCase(Locale.ROOT);
    if (!scheme.equals("http") && !scheme.equals("https")) {
      return new Classification(ReferrerAvailability.REFERRER_UNAVAILABLE, "", "", null);
    }
    String origin = originOf(uri);
    String path = Optional.ofNullable(uri.getPath()).orElse("");
    boolean hasPath = path.length() > 1;
    boolean hasQuery = uri.getQuery() != null && !uri.getQuery().isBlank();
    boolean hasFragment = uri.getFragment() != null && !uri.getFragment().isBlank();
    if (hasPath || hasQuery || hasFragment) {
      return new Classification(ReferrerAvailability.FULL_REFERRER_AVAILABLE, trimmed, origin, uri);
    }
    return new Classification(ReferrerAvailability.ORIGIN_ONLY, origin, origin, uri);
  }

  public static String originOf(URI uri) {
    int port = uri.getPort();
    String host = uri.getHost().toLowerCase(Locale.ROOT);
    String scheme = uri.getScheme().toLowerCase(Locale.ROOT);
    if (port < 0) {
      return scheme + "://" + host;
    }
    return scheme + "://" + host + ":" + port;
  }
}
