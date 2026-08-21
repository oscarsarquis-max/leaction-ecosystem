package br.com.banco.spider.execution.signal;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.evidence.reference.EvidenceReference;
import br.com.banco.spider.execution.domain.CanonicalOutcome;
import br.com.banco.spider.integration.port.AdapterDispositionMode;
import java.util.List;
import java.util.Objects;

public record SignalCompletion(
    AdapterDispositionMode disposition,
    CanonicalOutcome outcome,
    List<CanonicalError> errors,
    List<EvidenceReference> evidenceRefs) {

  public SignalCompletion {
    Objects.requireNonNull(disposition, "disposition");
    errors = errors == null ? List.of() : List.copyOf(errors);
    evidenceRefs = evidenceRefs == null ? List.of() : List.copyOf(evidenceRefs);
  }
}
