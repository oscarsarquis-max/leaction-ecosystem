package br.com.banco.spider.integration.port;

import br.com.banco.spider.evidence.reference.EvidenceReference;
import java.time.Instant;
import java.util.List;
import java.util.Objects;

/** Metadados de continuação assíncrona — sem URL/fila/tópico. Token opaco opcional (PROMPT-014). */
public record ContinuationDescriptor(
    String externalOperationRef,
    String waitSignalContractRef,
    Instant expiresAt,
    String sourceRef,
    List<EvidenceReference> evidenceRefs,
    String continuationToken) {

  public ContinuationDescriptor {
    Objects.requireNonNull(externalOperationRef, "externalOperationRef");
    externalOperationRef = externalOperationRef.trim();
    if (externalOperationRef.isEmpty()) {
      throw new IllegalArgumentException("externalOperationRef must not be blank");
    }
    waitSignalContractRef = blankToNull(waitSignalContractRef);
    sourceRef = blankToNull(sourceRef);
    evidenceRefs = evidenceRefs == null ? List.of() : List.copyOf(evidenceRefs);
    continuationToken = blankToNull(continuationToken);
  }

  /** Compat legado sem token. */
  public ContinuationDescriptor(
      String externalOperationRef,
      String waitSignalContractRef,
      Instant expiresAt,
      String sourceRef,
      List<EvidenceReference> evidenceRefs) {
    this(externalOperationRef, waitSignalContractRef, expiresAt, sourceRef, evidenceRefs, null);
  }

  private static String blankToNull(String v) {
    if (v == null || v.isBlank()) {
      return null;
    }
    return v.trim();
  }
}
