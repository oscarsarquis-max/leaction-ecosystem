package br.com.banco.spider.satellite.application;

import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextSnapshot;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Contribution;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Deterministic local-demo rules. Not actuarial, semantic or eligibility evaluation.
 */
public final class DemoSliceRules {

  public static final String FAMILY_SOURCE = "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1";
  public static final String INCOME_SOURCE = "SEGSENSE_INCOME_INTERRUPTION_SYNTHETIC_V1";
  public static final String FIRES_SOURCE = "SEGSENSE_NEARBY_FIRES_SYNTHETIC_V1";
  public static final String FAMILY_DECLARED = "SEGSENSE_DECLARED_FAMILY_CONTINUITY_V1";
  public static final String INCOME_DECLARED = "SEGSENSE_DECLARED_INCOME_INTERRUPTION_V1";
  public static final String FIRES_DECLARED = "SEGSENSE_DECLARED_NEARBY_FIRES_V1";
  public static final String HOME_DECLARED = "SEGSENSE_DECLARED_HOME_PROTECTION_V1";
  public static final String LEGACY_OBJECTIVE = "UNDERSTAND_FAMILY_PROTECTION_OPTIONS";
  public static final String UNDERSTAND = "UNDERSTAND_PROTECTION_OPTIONS";
  public static final String COMPARE = "COMPARE_COVERAGE_GAPS";
  public static final String SIMULATE_HOME = "SIMULATE_HOME_QUOTE";

  private DemoSliceRules() {}

  public static Decision evaluate(SatelliteInteractionRequest request) {
    ContextSnapshot snapshot = request.context() == null ? null : request.context().snapshot();
    String sourceId =
        snapshot == null || snapshot.provenance() == null ? "" : snapshot.provenance().sourceId();
    Map<String, String> attributes =
        snapshot == null || snapshot.attributes() == null ? Map.of() : snapshot.attributes();
    String constraint = attributes.getOrDefault("constraint", "");
    String objective = request.objective() == null ? "" : request.objective().text();
    List<Contribution> contributions =
        snapshot == null || snapshot.contributions() == null ? List.of() : snapshot.contributions();
    Contribution governed = firstRole(contributions, "GOVERNED_SOURCE");
    Contribution declared = firstRole(contributions, "VISITOR_DECLARED");
    String selected = snapshot == null ? null : snapshot.selectedContribution();
    String theme = resolveTheme(attributes, sourceId, selected, governed, declared);
    if ("unresolved_conflict".equals(constraint)) {
      return new Decision(
          "AMBIGUOUS",
          List.of(),
          null,
          sourceId,
          theme,
          clip(
              "A Spider aplicou regras explícitas e encontrou conflito entre as contribuições, sem escolha confirmada. Nenhum encaminhamento ao provedor foi feito."));
    }
    if ("missing_context".equals(constraint) || theme == null || theme.isBlank()) {
      return new Decision(
          "MISSING_CONTEXT",
          List.of("theme"),
          null,
          sourceId,
          theme,
          clip(
              "A Spider aplicou regras explícitas e o contexto estruturado não é suficiente para decidir. Nenhum encaminhamento ao provedor foi feito."));
    }
    if (SIMULATE_HOME.equals(objective)) {
      return evaluateHomeQuote(attributes, sourceId, theme, selected, governed, declared);
    }
    if (isHomeTheme(theme) && (UNDERSTAND.equals(objective) || COMPARE.equals(objective))) {
      return new Decision(
          "MISSING_CONTEXT",
          List.of("home_intention"),
          null,
          sourceId,
          theme,
          clip(
              "Esta fonte editorial trata de incêndios próximos de uma região hipotética. Ela não prova risco do imóvel. Diga se deseja avaliar uma proteção residencial em simulação."));
    }
    String scenarioSource = scenarioSourceId(sourceId, selected, governed, declared);
    String scenarioKey = scenarioKey(scenarioSource, objective);
    String explanation =
        clip(
            "A Spider aplicou regras explícitas ao contexto de "
                + humanTheme(theme)
                + " e à intenção de "
                + humanIntention(objective)
                + ". O resultado permite encaminhar o pedido ao provedor ilustrativo desta demonstração. "
                + consideredClause(governed, declared)
                + " Sem composição de seguro real.");
    return new Decision(
        "READY", List.of(), SatelliteContractV1.ILLUSTRATIVE_CAPABILITY, scenarioKey, theme, explanation);
  }

  private static Decision evaluateHomeQuote(
      Map<String, String> attributes,
      String sourceId,
      String theme,
      String selected,
      Contribution governed,
      Contribution declared) {
    if ("family_continuity".equals(theme) || "income_interruption".equals(theme)) {
      return new Decision(
          "AMBIGUOUS",
          List.of(),
          null,
          sourceId,
          theme,
          clip(
              "A intenção de proteção residencial não combina com o tema de continuidade familiar ou interrupção de renda sem escolha explícita."));
    }
    List<String> missing = new ArrayList<>();
    if (blank(attributes.get("dwellingType"))) {
      missing.add("dwelling_type");
    }
    if (blank(attributes.get("insuredAmountCents"))) {
      missing.add("insured_amount");
    }
    if (blank(attributes.get("coverPeriodMonths"))) {
      missing.add("cover_period");
    }
    String scenarioSource = scenarioSourceId(sourceId, selected, governed, declared);
    String scenarioKey = scenarioKey(scenarioSource, SIMULATE_HOME);
    if (!missing.isEmpty()) {
      return new Decision(
          "MISSING_CONTEXT",
          missing,
          null,
          scenarioKey,
          theme,
          clip(
              "Faltam dados sintéticos para calcular uma cotação simulada. O artigo sobre incêndios não substitui tipo de imóvel, capital nem período, e não agrava o preço."));
    }
    return new Decision(
        "READY",
        List.of(),
        SatelliteContractV1.HOME_QUOTE_CAPABILITY,
        scenarioKey,
        theme,
        clip(
            "A Spider aplicou regras explícitas ao contexto de "
                + humanTheme(theme)
                + " e à intenção de avaliar uma proteção residencial. Dados suficientes para pedir uma cotação simulada. Sem contratação real. "
                + consideredClause(governed, declared)));
  }

  public static String scenarioKey(String sourceId, String objective) {
    if (LEGACY_OBJECTIVE.equals(objective) || sourceId == null || sourceId.isBlank()) {
      return sourceId == null ? "" : sourceId;
    }
    return sourceId + "|" + objective;
  }

  public static String themeFromSource(String sourceId) {
    if (FAMILY_SOURCE.equals(sourceId) || FAMILY_DECLARED.equals(sourceId)) {
      return "family_continuity";
    }
    if (INCOME_SOURCE.equals(sourceId) || INCOME_DECLARED.equals(sourceId)) {
      return "income_interruption";
    }
    if (FIRES_SOURCE.equals(sourceId) || FIRES_DECLARED.equals(sourceId)) {
      return "nearby_fires";
    }
    if (HOME_DECLARED.equals(sourceId)) {
      return "home_protection";
    }
    return null;
  }

  public static Map<String, String> quoteInputs(Map<String, String> attributes) {
    if (attributes == null) {
      return Map.of();
    }
    List<String> keys = List.of("dwellingType", "insuredAmountCents", "coverPeriodMonths", "ratingRuleVersion");
    Map<String, String> inputs = new java.util.LinkedHashMap<>();
    for (String key : keys) {
      String value = attributes.get(key);
      if (!blank(value)) {
        inputs.put(key, value);
      }
    }
    inputs.putIfAbsent("ratingRuleVersion", "HOME_QUOTE_SYNTHETIC_V1");
    return inputs;
  }

  private static boolean isHomeTheme(String theme) {
    return "nearby_fires".equals(theme) || "home_protection".equals(theme);
  }

  private static String resolveTheme(
      Map<String, String> attributes,
      String sourceId,
      String selected,
      Contribution governed,
      Contribution declared) {
    String fromSelected = themeOf(selectedContribution(selected, governed, declared));
    return firstNonBlank(
        fromSelected, firstNonBlank(attributes.get("theme"), themeFromSource(sourceId)));
  }

  private static String scenarioSourceId(
      String headlineSourceId, String selected, Contribution governed, Contribution declared) {
    if ("VISITOR_DECLARED".equals(selected) && declared != null && declared.used()) {
      return declared.sourceId();
    }
    if (("GOVERNED_SOURCE".equals(selected) || "BOTH".equals(selected))
        && governed != null
        && governed.used()) {
      return governed.sourceId();
    }
    if (governed != null && governed.used()) {
      return governed.sourceId();
    }
    if (declared != null && declared.used()) {
      return declared.sourceId();
    }
    return headlineSourceId;
  }

  private static Contribution selectedContribution(
      String selected, Contribution governed, Contribution declared) {
    if ("VISITOR_DECLARED".equals(selected)) {
      return declared;
    }
    if ("GOVERNED_SOURCE".equals(selected)) {
      return governed;
    }
    if (governed != null && governed.used()) {
      return governed;
    }
    return declared;
  }

  private static String themeOf(Contribution contribution) {
    if (contribution == null || contribution.elements() == null) {
      return null;
    }
    return firstNonBlank(contribution.elements().get("theme"), themeFromSource(contribution.sourceId()));
  }

  private static Contribution firstRole(List<Contribution> contributions, String role) {
    for (Contribution contribution : contributions) {
      if (role.equals(contribution.role())) {
        return contribution;
      }
    }
    return null;
  }

  private static String consideredClause(Contribution governed, Contribution declared) {
    List<String> considered = new ArrayList<>();
    List<String> unused = new ArrayList<>();
    appendRole(governed, "fonte editorial", considered, unused);
    appendRole(declared, "relato declarado", considered, unused);
    StringBuilder text = new StringBuilder("Considerados: ");
    if (considered.isEmpty()) {
      text.append("o contexto estruturado desta fatia.");
    } else {
      text.append(String.join("; ", considered)).append('.');
    }
    if (!unused.isEmpty()) {
      text.append(" Não usados: ").append(String.join("; ", unused)).append('.');
    }
    return text.toString();
  }

  private static void appendRole(
      Contribution contribution, String label, List<String> considered, List<String> unused) {
    if (contribution == null) {
      return;
    }
    String theme =
        contribution.elements() == null ? "" : contribution.elements().getOrDefault("theme", "");
    String line = label + (theme.isBlank() ? "" : " (" + humanTheme(theme) + ")");
    if (contribution.used()) {
      considered.add(line);
    } else {
      unused.add(line);
    }
  }

  static String humanTheme(String theme) {
    if ("family_continuity".equals(theme)) {
      return "continuidade familiar";
    }
    if ("income_interruption".equals(theme)) {
      return "interrupção de renda";
    }
    if ("nearby_fires".equals(theme)) {
      return "proximidade de incêndios (editorial, não prova de risco do imóvel)";
    }
    if ("home_protection".equals(theme)) {
      return "proteção residencial declarada";
    }
    return "o contexto estruturado desta fatia";
  }

  static String humanIntention(String objective) {
    if (UNDERSTAND.equals(objective) || LEGACY_OBJECTIVE.equals(objective)) {
      return "entender opções ilustrativas de proteção";
    }
    if (COMPARE.equals(objective)) {
      return "comparar lacunas ilustrativas deste contexto";
    }
    if (SIMULATE_HOME.equals(objective)) {
      return "avaliar uma proteção residencial em simulação";
    }
    return "a intenção confirmada nesta fatia";
  }

  private static String firstNonBlank(String first, String second) {
    if (first != null && !first.isBlank()) {
      return first;
    }
    return second;
  }

  private static boolean blank(String value) {
    return value == null || value.isBlank();
  }

  private static String clip(String explanation) {
    if (explanation.length() <= 400) {
      return explanation;
    }
    return explanation.substring(0, 400);
  }

  public record Decision(
      String status,
      List<String> missingContext,
      String capabilityId,
      String scenarioKey,
      String theme,
      String explanation) {}
}
