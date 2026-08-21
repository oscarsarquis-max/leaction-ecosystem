package br.com.banco.spider.canonical.validation;

import br.com.banco.spider.canonical.error.CanonicalError;
import java.util.List;

/** Resultado tipado de validação — não usa exception como fluxo normal de rejeição. */
public record ValidationOutcome(boolean valid, List<CanonicalError> errors) {

  public ValidationOutcome {
    errors = errors == null ? List.of() : List.copyOf(errors);
  }

  public static ValidationOutcome ok() {
    return new ValidationOutcome(true, List.of());
  }

  public static ValidationOutcome rejected(List<CanonicalError> errors) {
    return new ValidationOutcome(false, errors);
  }

  public boolean hasBlockingErrors() {
    return !valid;
  }
}
