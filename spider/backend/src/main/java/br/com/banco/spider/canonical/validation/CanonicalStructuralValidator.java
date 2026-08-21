package br.com.banco.spider.canonical.validation;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.canonical.versioning.VersionedReference;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.port.CanonicalValidationPort;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.regex.Pattern;
import org.springframework.stereotype.Component;

/**
 * Validação estrutural inicial do envelope canônico (SPIDER-ARCH-003/004). Sem Spring Web/JPA.
 */
@Component
public class CanonicalStructuralValidator implements CanonicalValidationPort {

  private static final Pattern VERSION_PATTERN =
      Pattern.compile("^[0-9]+(\\.[0-9]+){0,3}([.-][A-Za-z0-9._-]+)?$");
  // W3C Trace Context — versão 00
  private static final Pattern TRACEPARENT_PATTERN =
      Pattern.compile("^[0-9a-f]{2}-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$");
  private static final Pattern URL_LIKE =
      Pattern.compile("(?i)^(https?://|http://|ftp://|ws://|wss://).*");

  @Override
  public ValidationOutcome validateRequest(
      CanonicalExecutionRequest request, OperationClass operationClass) {
    List<CanonicalError> errors = new ArrayList<>();
    if (request == null) {
      errors.add(validation("VAL_REQUEST_NULL", "request", "Request is required"));
      return ValidationOutcome.rejected(errors);
    }

    requireVersion(errors, "contract.schemaVersion", request.contract().schemaVersion());
    requireVersion(errors, "contract.contractVersion", request.contract().contractVersion());

    if (operationClass == OperationClass.EFFECT
        && (request.execution().idempotencyKey() == null
            || request.execution().idempotencyKey().isBlank())) {
      errors.add(
          validation(
              "VAL_IDEMPOTENCY_REQUIRED",
              "execution.idempotencyKey",
              "idempotencyKey is required for EFFECT operations"));
    }

    if (!TRACEPARENT_PATTERN.matcher(request.trace().traceparent()).matches()) {
      errors.add(
          validation(
              "VAL_TRACEPARENT_INVALID",
              "trace.traceparent",
              "traceparent must match W3C Trace Context format"));
    }

    if (request.callbackRef() != null) {
      rejectFreeUrl(errors, "callbackRef.ref", request.callbackRef().ref());
    }

    // target não deve parecer endpoint físico
    rejectFreeUrl(errors, "target.capability", request.target().capability());
    rejectFreeUrl(errors, "target.operation", request.target().operation());

    if (request.executionPolicy() != null && request.executionPolicy().timeout() != null) {
      if (request.executionPolicy().timeout().isNegative()
          || request.executionPolicy().timeout().isZero()) {
        errors.add(
            validation(
                "VAL_TIMEOUT_INVALID",
                "executionPolicy.timeout",
                "timeout must be a positive duration"));
      }
    }

    return errors.isEmpty() ? ValidationOutcome.ok() : ValidationOutcome.rejected(errors);
  }

  @Override
  public ValidationOutcome validateResult(CanonicalExecutionResult result) {
    List<CanonicalError> errors = new ArrayList<>();
    if (result == null) {
      errors.add(validation("VAL_RESULT_NULL", "result", "Result is required"));
      return ValidationOutcome.rejected(errors);
    }

    ExecutionState state = result.execution().state();
    if (state.isTerminal() && result.execution().completedAt() == null) {
      errors.add(
          validation(
              "VAL_COMPLETED_AT_REQUIRED",
              "execution.completedAt",
              "Terminal state requires completedAt"));
    }

    if (state == ExecutionState.SUCCEEDED) {
      boolean fatal =
          result.errors().stream().anyMatch(e -> e.severity() == ErrorSeverity.FATAL);
      if (fatal) {
        errors.add(
            validation(
                "VAL_SUCCEEDED_FATAL",
                "errors",
                "SUCCEEDED must not contain FATAL errors"));
      }
    }

    if (state == ExecutionState.FAILED
        || state == ExecutionState.REJECTED
        || state == ExecutionState.TIMED_OUT) {
      if (result.errors().isEmpty()) {
        errors.add(
            validation(
                "VAL_TERMINAL_ERROR_REQUIRED",
                "errors",
                "Failed terminal state requires at least one error"));
      }
    }

    if (result.outcome() != null
        && result.outcome().technicalStatus() == TechnicalStatus.SUCCESS
        && state == ExecutionState.FAILED) {
      errors.add(
          validation(
              "VAL_STATUS_INCOHERENT",
              "outcome.technicalStatus",
              "technicalStatus SUCCESS is incoherent with FAILED state"));
    }

    if (result.resolution() != null
        && (state == ExecutionState.RECEIVED || state == ExecutionState.VALIDATED)) {
      // resolution only after resolution — soft invariant as warning-level error entry
      errors.add(
          validation(
              "VAL_RESOLUTION_PREMATURE",
              "resolution",
              "resolution summary must appear only after resolution"));
    }

    return errors.isEmpty() ? ValidationOutcome.ok() : ValidationOutcome.rejected(errors);
  }

  private void requireVersion(List<CanonicalError> errors, String field, String value) {
    if (value == null || value.isBlank() || !VERSION_PATTERN.matcher(value.trim()).matches()) {
      errors.add(
          validation(
              "CON_UNSUPPORTED_VERSION",
              field,
              "Version format is invalid or unsupported"));
    }
  }

  private void rejectFreeUrl(List<CanonicalError> errors, String field, String value) {
    if (value != null && URL_LIKE.matcher(value.trim()).matches()) {
      errors.add(
          validation(
              "VAL_FREE_URL_FORBIDDEN",
              field,
              "Free URL/endpoint is forbidden; use a governed reference"));
    }
  }

  private CanonicalError validation(String code, String field, String message) {
    return CanonicalError.builder()
        .errorId("err-" + UUID.randomUUID())
        .code(code)
        .category(ErrorCategory.VALIDATION)
        .severity(ErrorSeverity.ERROR)
        .message(message)
        .retryable(false)
        .occurredAt(Instant.now())
        .source(new CanonicalError.ErrorSource("canonical-validator", null, null, null))
        .fieldViolations(
            List.of(new CanonicalError.FieldViolation(field, code, message)))
        .build();
  }

  /** Utilitário para testes de referência. */
  public static boolean looksLikeUrl(String value) {
    return value != null && URL_LIKE.matcher(value.trim()).matches();
  }

  public static boolean isValidTraceparent(String value) {
    return value != null && TRACEPARENT_PATTERN.matcher(value.trim()).matches();
  }
}
