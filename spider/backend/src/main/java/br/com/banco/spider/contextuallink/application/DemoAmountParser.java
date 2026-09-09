package br.com.banco.spider.contextuallink.application;

import java.math.BigDecimal;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Interpreta valor em formato brasileiro sem inventar quantia. */
public final class DemoAmountParser {

  private static final Pattern DIGITS = Pattern.compile("(\\d)");

  private DemoAmountParser() {}

  public static String parse(String raw) {
    if (raw == null || raw.isBlank()) {
      return null;
    }
    String trimmed = raw.trim();
    if (trimmed.chars().noneMatch(Character::isDigit)) {
      return null;
    }
    boolean commaDecimal = trimmed.contains(",");
    String normalized = trimmed.replace("R$", "").replace("r$", "").replace(" ", "");
    if (commaDecimal) {
      normalized = normalized.replace(".", "").replace(",", ".");
    } else if (normalized.matches(".*\\.\\d{3}(\\.\\d{3})*$")) {
      normalized = normalized.replace(".", "");
    }
    try {
      BigDecimal value = new BigDecimal(normalized.replaceAll("[^0-9.]", ""));
      if (value.compareTo(BigDecimal.ZERO) <= 0) {
        return null;
      }
      return value.stripTrailingZeros().toPlainString();
    } catch (NumberFormatException ignored) {
      Matcher matcher = DIGITS.matcher(trimmed);
      StringBuilder digits = new StringBuilder();
      while (matcher.find()) {
        digits.append(matcher.group(1));
      }
      if (digits.isEmpty()) {
        return null;
      }
      BigDecimal value = new BigDecimal(digits.toString());
      return value.compareTo(BigDecimal.ZERO) <= 0 ? null : value.toPlainString();
    }
  }
}
