package br.com.banco.spider.contextuallink.domain;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Extrai título, description e texto editorial. Não executa scripts; trata HTML como dado.
 */
public final class HtmlExcerptExtractor {

  private static final Pattern TITLE =
      Pattern.compile("(?is)<title[^>]*>(.*?)</title>");
  private static final Pattern META_DESCRIPTION =
      Pattern.compile(
          "(?is)<meta[^>]+name\\s*=\\s*[\"']description[\"'][^>]*content\\s*=\\s*[\"'](.*?)[\"'][^>]*>");
  private static final Pattern META_DESCRIPTION_REV =
      Pattern.compile(
          "(?is)<meta[^>]+content\\s*=\\s*[\"'](.*?)[\"'][^>]*name\\s*=\\s*[\"']description[\"'][^>]*>");
  private static final Pattern ARTICLE =
      Pattern.compile("(?is)<article[^>]*>(.*?)</article>");
  private static final Pattern SCRIPT_STYLE =
      Pattern.compile("(?is)<(script|style|noscript|iframe)\\b[^>]*>.*?</\\1>");
  private static final Pattern TAGS = Pattern.compile("(?is)<[^>]+>");
  private static final Pattern ENTITIES =
      Pattern.compile("&amp;|&lt;|&gt;|&quot;|&#39;|&nbsp;");

  private HtmlExcerptExtractor() {}

  public record Excerpt(String title, String description, String text) {}

  public static Excerpt extract(String html) {
    if (html == null || html.isBlank()) {
      return new Excerpt("", "", "");
    }
    String withoutActive = SCRIPT_STYLE.matcher(html).replaceAll(" ");
    String title = firstGroup(TITLE, withoutActive);
    String description = firstGroup(META_DESCRIPTION, html);
    if (description.isBlank()) {
      description = firstGroup(META_DESCRIPTION_REV, html);
    }
    String article = firstGroup(ARTICLE, withoutActive);
    String source = article.isBlank() ? withoutActive : article;
    String text = decode(TAGS.matcher(source).replaceAll(" "));
    if (text.length() > 4000) {
      text = text.substring(0, 4000);
    }
    return new Excerpt(decode(title), decode(description), text.trim());
  }

  private static String firstGroup(Pattern pattern, String html) {
    Matcher matcher = pattern.matcher(html);
    if (!matcher.find()) {
      return "";
    }
    return matcher.group(1) == null ? "" : matcher.group(1);
  }

  private static String decode(String raw) {
    if (raw == null) {
      return "";
    }
    String value = raw.replace("&nbsp;", " ");
    value = value.replace("&amp;", "&");
    value = value.replace("&lt;", "<");
    value = value.replace("&gt;", ">");
    value = value.replace("&quot;", "\"");
    value = value.replace("&#39;", "'");
    return ENTITIES.matcher(value).replaceAll(" ").replaceAll("\\s+", " ").trim();
  }
}
