package br.com.banco.spider.context.application.port;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import reactor.core.publisher.Mono;

/** Porta probabilística. Não conhece rota, capability, endpoint, adapter nem Spider Core. */
public interface ContextInterpretationProvider {

  String providerId();

  String modelId();

  Mono<ProviderResult> interpret(ProviderRequest request);

  record ProviderRequest(
      String objectiveText,
      String promptVersion,
      String contractSchemaVersion,
      List<AllowedIntent> allowedIntents) {
    public ProviderRequest {
      allowedIntents = List.copyOf(allowedIntents);
    }
  }

  record AllowedIntent(
      String intent, String domain, String objective, List<String> requiredEntityKeys) {
    public AllowedIntent {
      requiredEntityKeys = List.copyOf(requiredEntityKeys);
    }
  }

  record ProviderResult(
      ProviderStatus status,
      String intent,
      Map<String, String> entities,
      List<String> candidateIntents,
      BigDecimal confidence,
      Usage usage,
      long latencyMs) {
    public ProviderResult {
      entities = entities == null ? Map.of() : Map.copyOf(entities);
      candidateIntents = candidateIntents == null ? List.of() : List.copyOf(candidateIntents);
      usage = usage == null ? Usage.empty() : usage;
    }
  }

  record Usage(Integer inputTokens, Integer outputTokens, Integer totalTokens) {
    public static Usage empty() {
      return new Usage(null, null, null);
    }
  }

  enum ProviderStatus {
    MATCHED,
    AMBIGUOUS,
    UNSUPPORTED_INTENT
  }
}
