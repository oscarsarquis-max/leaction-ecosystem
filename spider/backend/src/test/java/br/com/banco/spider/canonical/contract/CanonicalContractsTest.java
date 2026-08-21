package br.com.banco.spider.canonical.contract;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.canonical.versioning.VersionedReference;
import br.com.banco.spider.execution.domain.CanonicalOutcome;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.ExecutionSummary;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;

class CanonicalContractsTest {

  private final ObjectMapper mapper =
      new ObjectMapper()
          .registerModule(new JavaTimeModule())
          .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);

  @Test
  void buildsValidRequest() {
    CanonicalExecutionRequest request = sampleRequest();
    assertEquals("1.0", request.contract().schemaVersion());
    assertEquals("CONSULTAR_LANCAMENTO", request.target().capability());
  }

  @Test
  void rejectsBlankRequiredField() {
    assertThrows(
        IllegalArgumentException.class,
        () -> new ContractDescriptor(" ", "1.0.0"));
  }

  @Test
  void errorsAndEvidenceNeverNullAndImmutable() {
    CanonicalExecutionResult result =
        CanonicalExecutionResult.builder()
            .contract(new ContractDescriptor("1.0", "1.0.0"))
            .execution(
                new ExecutionSummary(
                    "exec-1",
                    ExecutionState.SUCCEEDED,
                    Instant.parse("2026-08-21T12:00:00Z"),
                    Instant.parse("2026-08-21T12:00:01Z"),
                    Instant.parse("2026-08-21T12:00:01Z")))
            .contextRef(
                new ResultContextReference("ctx", "intent@1", "cap@1", "journey@1"))
            .trace(
                new ResultTraceDescriptor(
                    "corr",
                    "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"))
            .outcome(CanonicalOutcome.technical(TechnicalStatus.SUCCESS))
            .build();

    assertTrue(result.errors().isEmpty());
    assertTrue(result.evidenceRefs().isEmpty());
    assertThrows(UnsupportedOperationException.class, () -> result.errors().add(null));
  }

  @Test
  void enumSerializesByName() throws Exception {
    String json = mapper.writeValueAsString(ErrorCategory.VALIDATION);
    assertEquals("\"VALIDATION\"", json);
    assertEquals(ExecutionState.SUCCEEDED, mapper.readValue("\"SUCCEEDED\"", ExecutionState.class));
  }

  @Test
  void safeErrorHasNoSensitiveValueInViolation() {
    CanonicalError error =
        CanonicalError.builder()
            .errorId("err-1")
            .code("VAL_X")
            .category(ErrorCategory.VALIDATION)
            .severity(ErrorSeverity.ERROR)
            .message("Invalid field")
            .retryable(false)
            .occurredAt(Instant.parse("2026-08-21T12:00:00Z"))
            .source(new CanonicalError.ErrorSource("validator", null, null, null))
            .fieldViolations(
                List.of(
                    new CanonicalError.FieldViolation(
                        "origin.originatorId", "VAL_X", "must be present")))
            .build();
    assertTrue(error.message().contains("Invalid"));
    assertEquals("must be present", error.fieldViolations().get(0).message());
  }

  @Test
  void roundTripPreservesMeaning() throws Exception {
    CanonicalExecutionRequest original = sampleRequest();
    String json = mapper.writeValueAsString(original);
    CanonicalExecutionRequest restored = mapper.readValue(json, CanonicalExecutionRequest.class);
    assertEquals(original.execution().executionId(), restored.execution().executionId());
    assertEquals(original.trace().traceparent(), restored.trace().traceparent());
    assertEquals(original.target().operation(), restored.target().operation());
  }

  private CanonicalExecutionRequest sampleRequest() {
    return CanonicalExecutionRequest.builder()
        .contract(new ContractDescriptor("1.0", "1.0.0"))
        .execution(
            new ExecutionIdentity(
                "exec-1", Instant.parse("2026-08-21T12:00:00Z"), "idem-1"))
        .contextRef(
            new ContextReference(
                "ctx-1",
                "INTENT@1.0.0",
                "CAP@1.0.0",
                "PROD@1.0.0",
                "JOURNEY@1.0.0"))
        .origin(new OriginDescriptor("CHANNEL", "originator-1", null))
        .trace(
            new TraceDescriptor(
                "corr-1",
                "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
                null))
        .target(new TargetDescriptor("CONSULTAR_LANCAMENTO", "consultar"))
        .payload(CanonicalPayload.empty())
        .callbackRef(VersionedReference.of("callback:default", "1.0.0"))
        .build();
  }
}
