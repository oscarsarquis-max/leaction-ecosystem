package br.com.segsense.application.urlcapture;

import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * URL_EXTRACTOR_V2: bytes remain hashed separately; this class selects main text only. No remote JS.
 */
public final class HtmlTextExtractor {

  public static final String VERSION = "URL_EXTRACTOR_V2";
  public static final int MAX_NORMALIZED_CHARS = 32_768;
  public static final int EXCERPT_CHARS = 1_200;

  public static final String STRATEGY_MAIN = "MAIN_ELEMENT";
  public static final String STRATEGY_ARTICLE = "ARTICLE_ELEMENT";
  public static final String STRATEGY_ROLE_MAIN = "ROLE_MAIN";
  public static final String STRATEGY_MW_CONTENT = "MW_CONTENT_TEXT";
  public static final String STRATEGY_BODY_CONTENT = "BODY_CONTENT";
  public static final String STRATEGY_CONTENT_ID = "CONTENT_ID";
  public static final String STRATEGY_PLAIN_TEXT = "PLAIN_TEXT";
  public static final String STRATEGY_FALLBACK = "STRIP_CHROME_BODY_FALLBACK";
  public static final String STRATEGY_NONE = "NONE";

  private static final Pattern TITLE = Pattern.compile("(?is)<title[^>]*>(.*?)</title>");
  private static final Pattern HTML_LANG = Pattern.compile("(?is)<html[^>]*\\blang\\s*=\\s*['\"]([^'\"]+)['\"]");
  private static final Pattern SCRIPT = Pattern.compile("(?is)<script\\b[^>]*>.*?</script>");
  private static final Pattern STYLE = Pattern.compile("(?is)<style\\b[^>]*>.*?</style>");
  private static final Pattern NOSCRIPT = Pattern.compile("(?is)<noscript\\b[^>]*>.*?</noscript>");
  private static final Pattern TEMPLATE = Pattern.compile("(?is)<template\\b[^>]*>.*?</template>");
  private static final Pattern IFRAME = Pattern.compile("(?is)<iframe\\b[^>]*>.*?</iframe>");
  private static final Pattern TAG = Pattern.compile("(?is)<[^>]+>");
  private static final Pattern ENTITY = Pattern.compile("&(#x?[0-9a-fA-F]+|[a-zA-Z]+);");
  private static final Pattern SECRET =
      Pattern.compile("(?i)(authorization\\s*[:=]\\s*\\S+|bearer\\s+[A-Za-z0-9._\\-]+|api[_-]?key\\s*[:=]\\s*\\S+)");
  private static final Pattern BLOCK =
      Pattern.compile("(?is)<(p|h[1-6]|li|dd|dt|blockquote|caption)\\b[^>]*>(.*?)</\\1>");
  private static final Pattern HIDDEN =
      Pattern.compile(
          "(?is)<([a-z][a-z0-9]*)\\b[^>]*(?:\\bhidden\\b|aria-hidden\\s*=\\s*['\"]true['\"]|display\\s*:\\s*none|visibility\\s*:\\s*hidden)[^>]*>.*?</\\1>");
  private static final String[] CHROME_TAGS = {"nav", "header", "footer", "aside", "form", "menu"};
  private static final String[] CHROME_IDS = {
    "toc",
    "mw-navigation",
    "mw-panel",
    "mw-head",
    "mw-page-header",
    "siteSub",
    "catlinks",
    "jump-to-nav",
    "vector-toc",
    "p-search",
    "p-logo",
    "p-personal"
  };

  private HtmlTextExtractor() {}

  public record Extracted(
      String title,
      String language,
      String normalizedText,
      String excerpt,
      String selectionStrategy,
      boolean mainContentIsolated) {

    public boolean usable() {
      return mainContentIsolated && HtmlTextExtractor.meaningful(normalizedText);
    }
  }

  public static Extracted extract(byte[] body, String contentType) {
    Charset charset = charsetOf(contentType);
    String raw = new String(body == null ? new byte[0] : body, charset);
    String title = first(TITLE, raw);
    String language = first(HTML_LANG, raw);
    if (isPlainText(contentType)) {
      String normalized = normalizePlain(raw);
      return finish(title, language, normalized, STRATEGY_PLAIN_TEXT, meaningful(normalized));
    }
    String withoutNoise =
        IFRAME.matcher(
                TEMPLATE.matcher(NOSCRIPT.matcher(STYLE.matcher(SCRIPT.matcher(raw).replaceAll(" ")).replaceAll(" "))
                        .replaceAll(" "))
                    .replaceAll(" "))
            .replaceAll(" ");
    Selected selected = selectMain(withoutNoise);
    String cleaned = stripChrome(selected.html());
    cleaned = HIDDEN.matcher(cleaned).replaceAll(" ");
    String normalized = paragraphsOf(cleaned);
    if (normalized.isBlank()) {
      normalized = flatten(cleaned);
    }
    boolean isolated = selected.isolated() && meaningful(normalized);
    if (STRATEGY_FALLBACK.equals(selected.strategy())) {
      isolated = meaningful(normalized);
    }
    if (STRATEGY_NONE.equals(selected.strategy())) {
      isolated = false;
    }
    return finish(title, language, normalized, selected.strategy(), isolated);
  }

  public static boolean meaningful(String normalizedText) {
    if (normalizedText == null) {
      return false;
    }
    String letters = normalizedText.replaceAll("[^\\p{L}\\p{N}]+", "");
    return letters.length() >= 40;
  }

  static Charset charsetOf(String contentType) {
    if (contentType == null) {
      return StandardCharsets.UTF_8;
    }
    String lower = contentType.toLowerCase(Locale.ROOT);
    int idx = lower.indexOf("charset=");
    if (idx < 0) {
      return StandardCharsets.UTF_8;
    }
    String name = lower.substring(idx + 8).replace("\"", "").replace("'", "").split("[;\\s]", 2)[0].trim();
    try {
      return Charset.forName(name);
    } catch (RuntimeException ignored) {
      return StandardCharsets.UTF_8;
    }
  }

  private static Extracted finish(
      String title, String language, String normalized, String strategy, boolean isolated) {
    String clipped = normalized;
    if (clipped.length() > MAX_NORMALIZED_CHARS) {
      clipped = clipped.substring(0, MAX_NORMALIZED_CHARS);
    }
    String excerpt = clipped.length() <= EXCERPT_CHARS ? clipped : clipped.substring(0, EXCERPT_CHARS);
    return new Extracted(clip(title, 300), clip(language, 16), clipped, excerpt, strategy, isolated);
  }

  private record Selected(String html, String strategy, boolean isolated) {}

  private static Selected selectMain(String html) {
    String main = innerByTag(html, "main");
    if (hasText(main)) {
      return new Selected(main, STRATEGY_MAIN, true);
    }
    String article = innerByTag(html, "article");
    if (hasText(article)) {
      return new Selected(article, STRATEGY_ARTICLE, true);
    }
    String roleMain = innerByAttr(html, "role", "main");
    if (hasText(roleMain)) {
      return new Selected(roleMain, STRATEGY_ROLE_MAIN, true);
    }
    String mw = innerById(html, "mw-content-text");
    if (hasText(mw)) {
      return new Selected(mw, STRATEGY_MW_CONTENT, true);
    }
    String bodyContent = innerById(html, "bodyContent");
    if (hasText(bodyContent)) {
      return new Selected(bodyContent, STRATEGY_BODY_CONTENT, true);
    }
    String contentId = innerById(html, "content");
    if (hasText(contentId)) {
      return new Selected(contentId, STRATEGY_CONTENT_ID, true);
    }
    String body = innerByTag(html, "body");
    String remainder = stripChrome(body == null ? html : body);
    if (hasText(remainder)) {
      return new Selected(remainder, STRATEGY_FALLBACK, false);
    }
    return new Selected("", STRATEGY_NONE, false);
  }

  private static String stripChrome(String html) {
    if (html == null) {
      return "";
    }
    String current = html;
    for (String tag : CHROME_TAGS) {
      current = removeTag(current, tag);
    }
    for (String id : CHROME_IDS) {
      current = removeById(current, id);
    }
    current = removeByClass(current, "toc");
    current = removeByClass(current, "vector-header");
    current = removeByClass(current, "mw-jump-link");
    current = removeByClass(current, "mw-editsection");
    return current;
  }

  private static String paragraphsOf(String html) {
    Matcher matcher = BLOCK.matcher(html == null ? "" : html);
    List<String> blocks = new ArrayList<>();
    while (matcher.find()) {
      String text = flatten(matcher.group(2));
      if (text.replaceAll("[^\\p{L}\\p{N}]+", "").length() >= 8) {
        blocks.add(text);
      }
    }
    return String.join("\n\n", blocks);
  }

  private static String flatten(String html) {
    String stripped = TAG.matcher(html == null ? "" : html).replaceAll(" ");
    String decoded = decodeEntities(stripped);
    String redacted = SECRET.matcher(decoded).replaceAll("[redacted]");
    return collapse(redacted);
  }

  private static String normalizePlain(String raw) {
    String redacted = SECRET.matcher(raw == null ? "" : raw).replaceAll("[redacted]");
    String collapsed = redacted.replace('\u0000', ' ').replace("\r\n", "\n").replace('\r', '\n');
    collapsed = collapsed.replaceAll("[ \\t]+", " ").replaceAll("\\n{3,}", "\n\n").trim();
    if (collapsed.length() > MAX_NORMALIZED_CHARS) {
      collapsed = collapsed.substring(0, MAX_NORMALIZED_CHARS);
    }
    return collapsed;
  }

  private static boolean isPlainText(String contentType) {
    if (contentType == null) {
      return false;
    }
    String lower = contentType.toLowerCase(Locale.ROOT);
    return lower.startsWith("text/plain");
  }

  private static boolean hasText(String html) {
    if (html == null || html.isBlank()) {
      return false;
    }
    return flatten(html).replaceAll("[^\\p{L}\\p{N}]+", "").length() >= 12;
  }

  private static String innerByTag(String html, String tag) {
    Pattern start = Pattern.compile("(?i)<" + tag + "\\b[^>]*>");
    Matcher matcher = start.matcher(html);
    if (!matcher.find()) {
      return null;
    }
    int from = matcher.end();
    String lower = html.toLowerCase(Locale.ROOT);
    int to = lower.indexOf("</" + tag.toLowerCase(Locale.ROOT) + ">", from);
    if (to < 0) {
      return null;
    }
    return html.substring(from, to);
  }

  private static String innerById(String html, String id) {
    Pattern start =
        Pattern.compile("(?i)<([a-z][a-z0-9]*)\\b[^>]*\\bid\\s*=\\s*['\"]" + Pattern.quote(id) + "['\"][^>]*>");
    Matcher matcher = start.matcher(html);
    if (!matcher.find()) {
      return null;
    }
    return innerFromMatch(html, matcher);
  }

  private static String innerByAttr(String html, String attr, String value) {
    Pattern start =
        Pattern.compile(
            "(?i)<([a-z][a-z0-9]*)\\b[^>]*\\b"
                + Pattern.quote(attr)
                + "\\s*=\\s*['\"]"
                + Pattern.quote(value)
                + "['\"][^>]*>");
    Matcher matcher = start.matcher(html);
    if (!matcher.find()) {
      return null;
    }
    return innerFromMatch(html, matcher);
  }

  private static String innerFromMatch(String html, Matcher matcher) {
    String tag = matcher.group(1);
    int from = matcher.end();
    String lower = html.toLowerCase(Locale.ROOT);
    int to = lower.indexOf("</" + tag.toLowerCase(Locale.ROOT) + ">", from);
    if (to < 0) {
      return html.substring(from);
    }
    return html.substring(from, to);
  }

  private static String removeTag(String html, String tag) {
    Pattern pattern = Pattern.compile("(?is)<" + tag + "\\b[^>]*>.*?</" + tag + ">");
    return pattern.matcher(html).replaceAll(" ");
  }

  private static String removeById(String html, String id) {
    Pattern pattern =
        Pattern.compile("(?is)<([a-z][a-z0-9]*)\\b[^>]*\\bid\\s*=\\s*['\"]" + Pattern.quote(id) + "['\"][^>]*>.*?</\\1>");
    return pattern.matcher(html).replaceAll(" ");
  }

  private static String removeByClass(String html, String className) {
    Pattern pattern =
        Pattern.compile(
            "(?is)<([a-z][a-z0-9]*)\\b[^>]*\\bclass\\s*=\\s*['\"][^'\"]*\\b"
                + Pattern.quote(className)
                + "\\b[^'\"]*['\"][^>]*>.*?</\\1>");
    return pattern.matcher(html).replaceAll(" ");
  }

  private static String first(Pattern pattern, String raw) {
    Matcher matcher = pattern.matcher(raw);
    if (!matcher.find()) {
      return "";
    }
    return collapse(decodeEntities(matcher.group(1)));
  }

  private static String decodeEntities(String value) {
    Matcher matcher = ENTITY.matcher(value);
    StringBuffer out = new StringBuffer();
    while (matcher.find()) {
      matcher.appendReplacement(out, Matcher.quoteReplacement(entityValue(matcher.group(1))));
    }
    matcher.appendTail(out);
    return out.toString();
  }

  private static String entityValue(String body) {
    return switch (body.toLowerCase(Locale.ROOT)) {
      case "nbsp" -> " ";
      case "amp" -> "&";
      case "lt" -> "<";
      case "gt" -> ">";
      case "quot" -> "\"";
      case "apos" -> "'";
      default -> {
        if (body.startsWith("#x") || body.startsWith("#X")) {
          try {
            yield String.valueOf((char) Integer.parseInt(body.substring(2), 16));
          } catch (RuntimeException ignored) {
            yield " ";
          }
        }
        if (body.startsWith("#")) {
          try {
            yield String.valueOf((char) Integer.parseInt(body.substring(1)));
          } catch (RuntimeException ignored) {
            yield " ";
          }
        }
        yield " ";
      }
    };
  }

  private static String collapse(String value) {
    if (value == null) {
      return "";
    }
    return value.replace('\u0000', ' ').replaceAll("[\\r\\n\\t]+", " ").replaceAll(" +", " ").trim();
  }

  private static String clip(String value, int max) {
    if (value == null) {
      return "";
    }
    return value.length() <= max ? value : value.substring(0, max);
  }
}
