package br.com.banco.spider.execution.signal;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.execution.wait.WaitState;
import br.com.banco.spider.integration.port.AdapterDispositionMode;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Component;

@Component
public class ExternalSignalValidator {

  private final SpiderClock clock;

  public ExternalSignalValidator(SpiderClock clock) {
    this.clock = clock;
  }

  public List<CanonicalError> validate(
      ExternalSignalEnvelope signal, ExecutionWaitRecord wait, boolean authorizeOk) {
    List<CanonicalError> errors = new ArrayList<>();
    Instant now = clock.now();

    if (signal.messageId().isBlank() || signal.correlationId().isBlank()) {
      errors.add(err("SIGNAL_REQUIRED_FIELDS", "messageId and correlationId are required"));
    }
    if (signal.securityContext() == null || !signal.securityContext().isValidAt(now)) {
      errors.add(err("SIGNAL_SECURITY_EXPIRED", "Security context missing or expired"));
    }
    if (!authorizeOk) {
      errors.add(err("SIGNAL_UNAUTHORIZED", "Principal/source not authorized"));
    }
    if (!"1.0".equals(signal.signalContractVersion())
        && !"1.0.0".equals(signal.signalContractVersion())) {
      errors.add(err("SIGNAL_CONTRACT_VERSION", "Unsupported signal contract version"));
    }
    if (signal.completion().disposition() == AdapterDispositionMode.ACCEPTED_ASYNC) {
      errors.add(err("SIGNAL_NESTED_ASYNC", "Nested async completion rejected in this increment"));
    }

    if (wait == null) {
      return List.copyOf(errors);
    }

    if (wait.state() != WaitState.WAITING) {
      errors.add(err("SIGNAL_WAIT_NOT_ACTIVE", "Wait is not in WAITING state"));
    }
    if (!wait.executionId().equals(signal.executionId())
        || !wait.stepId().equals(signal.stepId())) {
      errors.add(err("SIGNAL_CORRELATION_MISMATCH", "execution/step does not match wait"));
    }
    if (wait.expectedSourceRef() != null
        && !wait.expectedSourceRef().equals(signal.sourceRef())) {
      errors.add(err("SIGNAL_SOURCE_MISMATCH", "Source not expected for wait"));
    }
    if (wait.expectedSignalContractRef() != null
        && !wait.expectedSignalContractRef().equals(signal.contractRef())) {
      errors.add(err("SIGNAL_CONTRACT_MISMATCH", "Contract not expected for wait"));
    }
    if (wait.externalOperationRef() != null
        && signal.externalOperationRef() != null
        && !wait.externalOperationRef().equals(signal.externalOperationRef())) {
      errors.add(err("SIGNAL_EXT_OP_MISMATCH", "externalOperationRef mismatch"));
    }
    if (now.isAfter(wait.expiresAt())) {
      errors.add(err("SIGNAL_WAIT_EXPIRED", "Wait deadline already passed"));
    }
    return List.copyOf(errors);
  }

  private static CanonicalError err(String code, String message) {
    return CanonicalError.builder()
        .errorId("err-" + UUID.randomUUID())
        .code(code)
        .category(ErrorCategory.VALIDATION)
        .severity(ErrorSeverity.ERROR)
        .message(message)
        .retryable(false)
        .occurredAt(Instant.now())
        .source(new CanonicalError.ErrorSource("external_signal", null, null, null))
        .build();
  }
}
