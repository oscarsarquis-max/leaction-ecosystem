package br.com.banco.spider.contextuallink.domain;

import java.net.URI;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Recusa query contextual no link do parceiro. O gateway ignora qualquer query recebida.
 */
public final class GenericLinkInspector {

  private static final Pattern CONTEXTUAL_QUERY =
      Pattern.compile(
          "(?i)\\b(intent|campaign|cropFailure|workingCapital|articleId|contextId|purpose|amount|produto|rota|capability)\\b");

  private GenericLinkInspector() {}

  public static boolean hasContextualQuery(String href) {
    if (href == null || href.isBlank()) {
      return false;
    }
    try {
      URI uri = URI.create(href.trim());
      String query = uri.getQuery();
      if (query == null || query.isBlank()) {
        return false;
      }
      return CONTEXTUAL_QUERY.matcher(query).find();
    } catch (IllegalArgumentException ex) {
      return false;
    }
  }

  public static boolean isGenericGatewayPath(String href, Set<String> acceptedExactHrefs) {
    if (href == null || href.isBlank()) {
      return false;
    }
    String trimmed = href.trim();
    if (acceptedExactHrefs.contains(trimmed)) {
      return !hasContextualQuery(trimmed);
    }
    try {
      URI uri = URI.create(trimmed);
      String path = OptionalPath(uri);
      return "/go".equals(path) && (uri.getQuery() == null || uri.getQuery().isBlank());
    } catch (IllegalArgumentException ex) {
      return false;
    }
  }

  private static String OptionalPath(URI uri) {
    String path = uri.getPath();
    if (path == null || path.isBlank()) {
      return "/";
    }
    return path.toLowerCase(Locale.ROOT);
  }
}
