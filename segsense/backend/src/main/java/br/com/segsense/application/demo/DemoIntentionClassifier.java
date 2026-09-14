package br.com.segsense.application.demo;

import java.util.Locale;

public final class DemoIntentionClassifier {

  public static final String SIMULATE_HOME_QUOTE = "SIMULATE_HOME_QUOTE";
  public static final String UNDERSTAND = "UNDERSTAND_PROTECTION_OPTIONS";
  public static final String COMPARE = "COMPARE_COVERAGE_GAPS";
  public static final String EFFECTIVE_CONTRACT = "REQUEST_EFFECTIVE_CONTRACT";
  public static final String UNRECOGNIZED = "UNRECOGNIZED";

  private DemoIntentionClassifier() {}

  public static String code(String text) {
    if (text == null || text.isBlank()) {
      return UNRECOGNIZED;
    }
    String normalized = text.toLowerCase(Locale.ROOT);
    if (containsAny(
        normalized,
        "emitir apólice",
        "emitir apolice",
        "pagar agora",
        "assinar contrato",
        "contratação efetiva",
        "contratacao efetiva",
        "proposta vinculante",
        "cotação vinculante",
        "cotacao vinculante")) {
      return EFFECTIVE_CONTRACT;
    }
    if (containsAny(normalized, "comparar lacunas", "comparar cobertura", "lacunas ilustrativas")) {
      return COMPARE;
    }
    if (containsAny(
        normalized,
        "seguro residencial",
        "proteção residencial",
        "protecao residencial",
        "proteger a casa",
        "proteger o imóvel",
        "proteger o imovel",
        "cotar residencial",
        "contratar um seguro residencial",
        "contratar seguro residencial")) {
      return SIMULATE_HOME_QUOTE;
    }
    if (containsAny(normalized, "entender opções", "entender opcoes", "opções ilustrativas", "opcoes ilustrativas")) {
      return UNDERSTAND;
    }
    return UNRECOGNIZED;
  }

  public static String interpretation(String code) {
    if (SIMULATE_HOME_QUOTE.equals(code)) {
      return "Entendi que você quer avaliar uma proteção residencial.";
    }
    if (UNDERSTAND.equals(code)) {
      return "Entendi que você quer entender opções ilustrativas de proteção.";
    }
    if (COMPARE.equals(code)) {
      return "Entendi que você quer comparar opções ilustrativas deste contexto.";
    }
    if (EFFECTIVE_CONTRACT.equals(code)) {
      return "Contratar de verdade depende de seguradora e produto autorizados. Esta fatia só simula.";
    }
    return "Não reconheci o que você deseja. Diga, por exemplo, que quer avaliar uma proteção residencial.";
  }

  public static boolean isEffectiveContract(String text) {
    return EFFECTIVE_CONTRACT.equals(code(text));
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
