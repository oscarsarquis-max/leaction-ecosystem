package br.com.banco.spider.integration.outbound.ai;

import br.com.banco.spider.context.application.port.ContextInterpretationProvider;
import java.math.BigDecimal;
import java.text.Normalizer;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Pattern;
import reactor.core.publisher.Mono;

/**
 * Provider local explícito para testes/evidências sem cloud.
 *
 * <p>Nunca é habilitado por padrão e não é apresentado como smoke de IA real.
 */
public final class ScriptedContextInterpretationProvider
    implements ContextInterpretationProvider {

  private static final Pattern PROPOSAL_ID =
      Pattern.compile(
          "(?i)\\bproposta(?:\\s+(?:n[ºo.]|numero))?\\s*[:#-]?\\s*([A-Z0-9-]*\\d[A-Z0-9-]*)");
  private static final Pattern AMOUNT =
      Pattern.compile(
          "(?i)(?:R\\$\\s*)?(\\d+(?:\\.\\d{3})*)(?:,(\\d{1,2}))?\\s*(mil)?\\b");

  @Override
  public String providerId() {
    return "scripted-evidence";
  }

  @Override
  public String modelId() {
    return "controlled-vocabulary-v1";
  }

  @Override
  public Mono<ProviderResult> interpret(ProviderRequest request) {
    long started = System.nanoTime();
    String text = request.objectiveText();
    String normalized = normalized(text);
    ProviderResult result;
    if (normalized.contains("passagem") || normalized.contains("paris")) {
      result =
          new ProviderResult(
              ProviderStatus.UNSUPPORTED_INTENT,
              null,
              Map.of(),
              List.of(),
              new BigDecimal("0.99"),
              Usage.empty(),
              elapsed(started));
    } else if (normalized.contains("cliente")
        && !(normalized.contains("cadastro")
            || normalized.contains("cobran")
            || normalized.contains("atendimento"))) {
      result =
          new ProviderResult(
              ProviderStatus.AMBIGUOUS,
              null,
              Map.of(),
              List.of(
                  "CHECK_CUSTOMER_DATA_INCONSISTENCY",
                  "INVESTIGATE_SERVICE_REQUEST",
                  "INVESTIGATE_COLLECTION_PENDING"),
              new BigDecimal("0.62"),
              Usage.empty(),
              elapsed(started));
    } else {
      String intent = knownIntent(normalized);
      if (intent == null) {
        result =
            new ProviderResult(
                ProviderStatus.UNSUPPORTED_INTENT,
                null,
                Map.of(),
                List.of(),
                new BigDecimal("0.55"),
                Usage.empty(),
                elapsed(started));
      } else {
        Map<String, String> entities =
            "INVESTIGATE_CREDIT_RELEASE".equals(intent)
                ? proposalEntity(text)
                : "SEEK_WORKING_CAPITAL".equals(intent)
                    ? workingCapitalEntities(text, normalized)
                    : Map.of();
        result =
            new ProviderResult(
                ProviderStatus.MATCHED,
                intent,
                entities,
                List.of(),
                new BigDecimal("0.94"),
                Usage.empty(),
                elapsed(started));
      }
    }
    return Mono.just(result);
  }

  private static String knownIntent(String text) {
    if (text.contains("capital de giro")
        || text.contains("reforcar meu estoque")
        || text.contains("reforcar o estoque")
        || text.contains("reforcar o caixa")
        || text.contains("materia-prima")
        || text.contains("antecipar a compra de mercadorias")) {
      return "SEEK_WORKING_CAPITAL";
    }
    if (text.contains("proposta") || text.contains("credito")) {
      return "INVESTIGATE_CREDIT_RELEASE";
    }
    if (text.contains("cobran")) return "INVESTIGATE_COLLECTION_PENDING";
    if (text.contains("fatur") || text.contains("nota fiscal")) {
      return "INVESTIGATE_BILLING_FAILURE";
    }
    if (text.contains("cadastro") || text.contains("dados do cliente")) {
      return "CHECK_CUSTOMER_DATA_INCONSISTENCY";
    }
    if (text.contains("atendimento") || text.contains("solicitação")) {
      return "INVESTIGATE_SERVICE_REQUEST";
    }
    if (text.contains("incidente")) return "INVESTIGATE_INCIDENT";
    return null;
  }

  private static Map<String, String> proposalEntity(String text) {
    var matcher = PROPOSAL_ID.matcher(text);
    return matcher.find() ? Map.of("proposalId", matcher.group(1)) : Map.of();
  }

  private static Map<String, String> workingCapitalEntities(String text, String normalized) {
    Map<String, String> entities = new LinkedHashMap<>();
    if (normalized.contains("materia-prima")) {
      entities.put("purpose", "RAW_MATERIAL");
      entities.put("businessSituation", "NEW_ORDERS_PRODUCTION_INCREASE");
    } else if (normalized.contains("sazon")
        || normalized.contains("periodo de maior movimento")
        || normalized.contains("antecipar a compra de mercadorias")) {
      entities.put("purpose", "SEASONALITY");
      entities.put("businessSituation", "SEASONAL_DEMAND");
    } else if (normalized.contains("caixa")
        || normalized.contains("despesas operacionais")) {
      entities.put("purpose", "CASH_FLOW");
      entities.put("businessSituation", "TEMPORARY_OPERATING_EXPENSE_INCREASE");
    } else if (normalized.contains("estoque") || normalized.contains("mercadorias")) {
      entities.put("purpose", "INVENTORY");
      entities.put("businessSituation", "SALES_GROWTH");
    }
    String amount = explicitAmount(text);
    if (amount != null) {
      entities.put("amount", amount);
    }
    return Map.copyOf(entities);
  }

  private static String explicitAmount(String text) {
    var matcher = AMOUNT.matcher(text);
    if (!matcher.find()) {
      return null;
    }
    String integer = matcher.group(1).replace(".", "");
    BigDecimal value =
        new BigDecimal(integer + (matcher.group(2) == null ? "" : "." + matcher.group(2)));
    if (matcher.group(3) != null) {
      value = value.multiply(new BigDecimal("1000"));
    }
    return value.stripTrailingZeros().toPlainString();
  }

  private static String normalized(String text) {
    return Normalizer.normalize(text, Normalizer.Form.NFD)
        .replaceAll("\\p{M}+", "")
        .toLowerCase(Locale.ROOT);
  }

  private static long elapsed(long started) {
    return Math.max(0, (System.nanoTime() - started) / 1_000_000);
  }
}
