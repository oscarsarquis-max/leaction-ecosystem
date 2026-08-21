package br.com.banco.spider.evidence.reference;

import java.util.Objects;

/**
 * Referência protegida a evidência técnica — não carrega payload de negócio.
 *
 * @param evidenceId identidade opaca da evidência
 * @param kind classificação lógica (ex.: adapter-interaction, validation)
 */
public record EvidenceReference(String evidenceId, String kind) {

  public EvidenceReference {
    Objects.requireNonNull(evidenceId, "evidenceId");
    evidenceId = evidenceId.trim();
    if (evidenceId.isEmpty()) {
      throw new IllegalArgumentException("evidenceId must not be blank");
    }
    if (kind != null) {
      kind = kind.trim();
      if (kind.isEmpty()) {
        kind = null;
      }
    }
  }
}
