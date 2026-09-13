package br.com.segsense.domain.opportunity;

import java.util.Objects;

public final class AdministrativeJustification {

  private final String value;

  private AdministrativeJustification(String value) {
    this.value = value;
  }

  public static AdministrativeJustification required(String raw) {
    if (raw == null || raw.isBlank()) {
      throw new JustificationRequiredException();
    }
    String value = OpportunityText.requiredLength(raw, "A justificativa", 10, 500);
    return new AdministrativeJustification(value);
  }

  public static AdministrativeJustification optional(String raw) {
    if (raw == null || raw.isBlank()) {
      return null;
    }
    return required(raw);
  }

  public String value() {
    return value;
  }

  @Override
  public boolean equals(Object other) {
    if (this == other) {
      return true;
    }
    if (!(other instanceof AdministrativeJustification that)) {
      return false;
    }
    return Objects.equals(value, that.value);
  }

  @Override
  public int hashCode() {
    return Objects.hash(value);
  }
}
