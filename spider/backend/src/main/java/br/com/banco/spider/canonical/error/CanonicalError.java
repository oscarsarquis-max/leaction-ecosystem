package br.com.banco.spider.canonical.error;

import java.time.Instant;
import java.util.List;
import java.util.Objects;

/** Erro canônico seguro (SPIDER-ARCH-004). Imutável; sem stack/secrets/topologia. */
public record CanonicalError(
    String errorId,
    String code,
    ErrorCategory category,
    ErrorSeverity severity,
    String message,
    boolean retryable,
    Instant occurredAt,
    ErrorSource source,
    String causeRef,
    String detailsRef,
    List<FieldViolation> fieldViolations) {

  public CanonicalError {
    Objects.requireNonNull(errorId, "errorId");
    Objects.requireNonNull(code, "code");
    Objects.requireNonNull(category, "category");
    Objects.requireNonNull(severity, "severity");
    Objects.requireNonNull(message, "message");
    Objects.requireNonNull(occurredAt, "occurredAt");
    Objects.requireNonNull(source, "source");
    errorId = errorId.trim();
    code = code.trim();
    message = message.trim();
    if (errorId.isEmpty() || code.isEmpty() || message.isEmpty()) {
      throw new IllegalArgumentException("errorId, code and message must not be blank");
    }
    fieldViolations =
        fieldViolations == null ? List.of() : List.copyOf(fieldViolations);
  }

  public record ErrorSource(
      String component, String stepId, String adapterId, String targetRef) {

    public ErrorSource {
      Objects.requireNonNull(component, "component");
      component = component.trim();
      if (component.isEmpty()) {
        throw new IllegalArgumentException("component must not be blank");
      }
      stepId = blankToNull(stepId);
      adapterId = blankToNull(adapterId);
      targetRef = blankToNull(targetRef);
    }

    private static String blankToNull(String v) {
      if (v == null) {
        return null;
      }
      String t = v.trim();
      return t.isEmpty() ? null : t;
    }
  }

  /** Violação de campo sem expor valor sensível. */
  public record FieldViolation(String fieldPath, String reasonCode, String message) {

    public FieldViolation {
      Objects.requireNonNull(fieldPath, "fieldPath");
      Objects.requireNonNull(reasonCode, "reasonCode");
      Objects.requireNonNull(message, "message");
      fieldPath = fieldPath.trim();
      reasonCode = reasonCode.trim();
      message = message.trim();
    }
  }

  public static Builder builder() {
    return new Builder();
  }

  public static final class Builder {
    private String errorId;
    private String code;
    private ErrorCategory category;
    private ErrorSeverity severity = ErrorSeverity.ERROR;
    private String message;
    private boolean retryable;
    private Instant occurredAt = Instant.now();
    private ErrorSource source;
    private String causeRef;
    private String detailsRef;
    private List<FieldViolation> fieldViolations = List.of();

    public Builder errorId(String errorId) {
      this.errorId = errorId;
      return this;
    }

    public Builder code(String code) {
      this.code = code;
      return this;
    }

    public Builder category(ErrorCategory category) {
      this.category = category;
      return this;
    }

    public Builder severity(ErrorSeverity severity) {
      this.severity = severity;
      return this;
    }

    public Builder message(String message) {
      this.message = message;
      return this;
    }

    public Builder retryable(boolean retryable) {
      this.retryable = retryable;
      return this;
    }

    public Builder occurredAt(Instant occurredAt) {
      this.occurredAt = occurredAt;
      return this;
    }

    public Builder source(ErrorSource source) {
      this.source = source;
      return this;
    }

    public Builder causeRef(String causeRef) {
      this.causeRef = causeRef;
      return this;
    }

    public Builder detailsRef(String detailsRef) {
      this.detailsRef = detailsRef;
      return this;
    }

    public Builder fieldViolations(List<FieldViolation> fieldViolations) {
      this.fieldViolations = fieldViolations;
      return this;
    }

    public CanonicalError build() {
      return new CanonicalError(
          errorId,
          code,
          category,
          severity,
          message,
          retryable,
          occurredAt,
          source,
          causeRef,
          detailsRef,
          fieldViolations);
    }
  }
}
