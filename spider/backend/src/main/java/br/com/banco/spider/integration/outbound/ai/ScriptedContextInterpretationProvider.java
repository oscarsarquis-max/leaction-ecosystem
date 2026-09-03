package br.com.banco.spider.integration.outbound.ai;

import br.com.banco.spider.context.application.port.ContextInterpretationProvider;
import java.math.BigDecimal;
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
    String normalized = text.toLowerCase(Locale.ROOT);
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
    if (text.contains("proposta") || text.contains("crédito") || text.contains("credito")) {
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

  private static long elapsed(long started) {
    return Math.max(0, (System.nanoTime() - started) / 1_000_000);
  }
}
