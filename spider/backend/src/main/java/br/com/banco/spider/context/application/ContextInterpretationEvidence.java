package br.com.banco.spider.context.application;

import br.com.banco.spider.context.application.port.ContextInterpretationProvider;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;

/** Evidência segura e estruturada da interpretação; nunca contém chain-of-thought ou secrets. */
public record ContextInterpretationEvidence(
    String interpretationId,
    String requestedObjective,
    String provider,
    String model,
    Instant interpretedAt,
    String promptVersion,
    String schemaVersion,
    String intent,
    String domain,
    Map<String, String> extractedEntities,
    List<String> missingContext,
    List<String> candidateIntents,
    BigDecimal confidence,
    ContextInterpretationProvider.Usage usage,
    long latencyMs,
    int redactedFieldsCount) {

  public ContextInterpretationEvidence {
    extractedEntities =
        extractedEntities == null ? Map.of() : Map.copyOf(extractedEntities);
    missingContext = missingContext == null ? List.of() : List.copyOf(missingContext);
    candidateIntents = candidateIntents == null ? List.of() : List.copyOf(candidateIntents);
    usage = usage == null ? ContextInterpretationProvider.Usage.empty() : usage;
  }
}
