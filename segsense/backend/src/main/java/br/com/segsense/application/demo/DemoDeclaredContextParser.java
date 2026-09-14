package br.com.segsense.application.demo;

import java.util.Locale;

public final class DemoDeclaredContextParser {

  public static final String FAMILY = "family_continuity";
  public static final String INCOME = "income_interruption";
  public static final String FIRES = "nearby_fires";

  private DemoDeclaredContextParser() {}

  public static String themeFromDeclaredText(String text) {
    if (text == null || text.isBlank()) {
      return null;
    }
    String normalized = text.toLowerCase(Locale.ROOT);
    boolean family =
        containsAny(normalized, "continuidade familiar", "dependentes", "família", "familia");
    boolean income =
        containsAny(normalized, "interrupção de renda", "interrupcao de renda", "parar de trabalhar", "renda do trabalho");
    boolean fires =
        containsAny(
            normalized,
            "incêndios nas proximidades",
            "incendios nas proximidades",
            "incêndios próximos",
            "incendios proximos",
            "incêndios perto",
            "houve incêndios",
            "houve incendios");
    if (family && income || family && fires || income && fires) {
      return "conflict";
    }
    if (family) {
      return FAMILY;
    }
    if (income) {
      return INCOME;
    }
    if (fires) {
      return FIRES;
    }
    return null;
  }

  private static boolean containsAny(String haystack, String... needles) {
    for (String needle : needles) {
      if (haystack.contains(needle)) {
        return true;
      }
    }
    return false;
  }
}
