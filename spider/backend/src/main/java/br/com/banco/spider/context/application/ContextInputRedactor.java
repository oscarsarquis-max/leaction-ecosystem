package br.com.banco.spider.context.application;

import java.util.List;
import java.util.regex.Pattern;

/** Redação mínima antes da fronteira externa do provider. */
public final class ContextInputRedactor {

  private static final String REDACTED = "[REDACTED]";
  private static final List<Rule> RULES =
      List.of(
          new Rule(
              Pattern.compile("(?i)\\bbearer\\s+[a-z0-9._~+/=-]+"),
              "Bearer " + REDACTED),
          new Rule(
              Pattern.compile(
                  "(?i)\\b(authorization|token|secret|password|api[-_ ]?key)\\s*[:=]\\s*\\S+"),
              "$1=" + REDACTED),
          new Rule(Pattern.compile("\\bAKIA[0-9A-Z]{16}\\b"), "[REDACTED_AWS_ACCESS_KEY]"),
          new Rule(
              Pattern.compile("\\b\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}\\b"),
              "[REDACTED_CPF]"),
          new Rule(
              Pattern.compile(
                  "(?i)\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}\\b"),
              "[REDACTED_EMAIL]"));

  private final int maxInputChars;

  public ContextInputRedactor(int maxInputChars) {
    this.maxInputChars = Math.max(256, maxInputChars);
  }

  public RedactionResult redact(String input) {
    String value = input == null ? "" : input.strip();
    int count = 0;
    for (Rule rule : RULES) {
      var matcher = rule.pattern().matcher(value);
      StringBuffer output = new StringBuffer();
      boolean changed = false;
      while (matcher.find()) {
        count++;
        changed = true;
        matcher.appendReplacement(output, rule.replacement());
      }
      if (changed) {
        matcher.appendTail(output);
        value = output.toString();
      }
    }
    if (value.length() > maxInputChars) {
      value = value.substring(0, maxInputChars);
      count++;
    }
    return new RedactionResult(value, count);
  }

  private record Rule(Pattern pattern, String replacement) {}

  public record RedactionResult(String safeObjective, int redactedFieldsCount) {}
}
