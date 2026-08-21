package br.com.banco.spider.canonical.validation;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.canonical.contract.CanonicalPayload;
import br.com.banco.spider.canonical.contract.ContextReference;
import br.com.banco.spider.canonical.contract.ContractDescriptor;
import br.com.banco.spider.canonical.contract.ExecutionIdentity;
import br.com.banco.spider.canonical.contract.OriginDescriptor;
import br.com.banco.spider.canonical.contract.ResultContextReference;
import br.com.banco.spider.canonical.contract.ResultTraceDescriptor;
import br.com.banco.spider.canonical.contract.TargetDescriptor;
import br.com.banco.spider.canonical.contract.TraceDescriptor;
import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.canonical.versioning.VersionedReference;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.ExecutionSummary;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;

class CanonicalStructuralValidatorTest {

  private final CanonicalStructuralValidator validator = new CanonicalStructuralValidator();

  @Test
  void acceptsValidEffectRequest() {
    ValidationOutcome outcome =
        validator.validateRequest(validRequest("idem-1"), OperationClass.EFFECT);
    assertTrue(outcome.valid());
  }

  @Test
  void rejectsMissingIdempotencyForEffect() {
    CanonicalExecutionRequest request =
        CanonicalExecutionRequest.builder()
            .contract(new ContractDescriptor("1.0", "1.0.0"))
            .execution(new ExecutionIdentity("exec-1", Instant.now(), null))
            .contextRef(
                new ContextReference("c", "i@1", "cap@1", "p@1", "j@1"))
            .origin(new OriginDescriptor("CH", "orig", null))
            .trace(
                new TraceDescriptor(
                    "corr",
                    "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
                    null))
            .target(new TargetDescriptor("CAP", "OP"))
            .payload(CanonicalPayload.empty())
            .build();
    ValidationOutcome outcome = validator.validateRequest(request, OperationClass.EFFECT);
    assertFalse(outcome.valid());
    assertTrue(
        outcome.errors().stream().anyMatch(e -> e.code().equals("VAL_IDEMPOTENCY_REQUIRED")));
  }

  @Test
  void rejectsCallbackFreeUrl() {
    CanonicalExecutionRequest request =
        CanonicalExecutionRequest.builder()
            .contract(new ContractDescriptor("1.0", "1.0.0"))
            .execution(new ExecutionIdentity("exec-1", Instant.now(), "idem"))
            .contextRef(new ContextReference("c", "i@1", "cap@1", "p@1", "j@1"))
            .origin(new OriginDescriptor("CH", "orig", null))
            .trace(
                new TraceDescriptor(
                    "corr",
                    "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
                    null))
            .target(new TargetDescriptor("CAP", "OP"))
            .payload(CanonicalPayload.empty())
            .callbackRef(VersionedReference.of("https://evil.example/callback"))
            .build();
    ValidationOutcome outcome = validator.validateRequest(request, OperationClass.EFFECT);
    assertFalse(outcome.valid());
    assertTrue(
        outcome.errors().stream().anyMatch(e -> e.code().equals("VAL_FREE_URL_FORBIDDEN")));
  }

  @Test
  void rejectsInvalidTraceparent() {
    CanonicalExecutionRequest request =
        CanonicalExecutionRequest.builder()
            .contract(new ContractDescriptor("1.0", "1.0.0"))
            .execution(new ExecutionIdentity("exec-1", Instant.now(), "idem"))
            .contextRef(new ContextReference("c", "i@1", "cap@1", "p@1", "j@1"))
            .origin(new OriginDescriptor("CH", "orig", null))
            .trace(new TraceDescriptor("corr", "bad-trace", null))
            .target(new TargetDescriptor("CAP", "OP"))
            .payload(CanonicalPayload.empty())
            .build();
    ValidationOutcome outcome = validator.validateRequest(request, OperationClass.EFFECT);
    assertFalse(outcome.valid());
  }

  @Test
  void resultInvariantSucceededRejectsFatal() {
    CanonicalExecutionResult result =
        CanonicalExecutionResult.builder()
            .contract(new ContractDescriptor("1.0", "1.0.0"))
            .execution(
                new ExecutionSummary(
                    "exec-1",
                    ExecutionState.SUCCEEDED,
                    Instant.now(),
                    Instant.now(),
                    Instant.now()))
            .contextRef(new ResultContextReference("c", "i", "cap", "j"))
            .trace(
                new ResultTraceDescriptor(
                    "corr",
                    "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"))
            .errors(
                List.of(
                    CanonicalError.builder()
                        .errorId("e1")
                        .code("INT_X")
                        .category(ErrorCategory.INTERNAL)
                        .severity(ErrorSeverity.FATAL)
                        .message("fatal")
                        .retryable(false)
                        .occurredAt(Instant.now())
                        .source(new CanonicalError.ErrorSource("t", null, null, null))
                        .build()))
            .build();
    assertFalse(validator.validateResult(result).valid());
  }

  @Test
  void failedRequiresError() {
    CanonicalExecutionResult result =
        CanonicalExecutionResult.builder()
            .contract(new ContractDescriptor("1.0", "1.0.0"))
            .execution(
                new ExecutionSummary(
                    "exec-1",
                    ExecutionState.FAILED,
                    Instant.now(),
                    Instant.now(),
                    Instant.now()))
            .contextRef(new ResultContextReference("c", "i", "cap", "j"))
            .trace(
                new ResultTraceDescriptor(
                    "corr",
                    "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"))
            .build();
    assertFalse(validator.validateResult(result).valid());
  }

  private CanonicalExecutionRequest validRequest(String idem) {
    return CanonicalExecutionRequest.builder()
        .contract(new ContractDescriptor("1.0", "1.0.0"))
        .execution(new ExecutionIdentity("exec-1", Instant.now(), idem))
        .contextRef(new ContextReference("c", "i@1", "cap@1", "p@1", "j@1"))
        .origin(new OriginDescriptor("CH", "orig", null))
        .trace(
            new TraceDescriptor(
                "corr",
                "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
                null))
        .target(new TargetDescriptor("CAP", "OP"))
        .payload(CanonicalPayload.empty())
        .callbackRef(VersionedReference.of("callback:default", "1.0.0"))
        .build();
  }
}
