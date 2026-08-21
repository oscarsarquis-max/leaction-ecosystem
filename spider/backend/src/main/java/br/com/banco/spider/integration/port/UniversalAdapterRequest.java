package br.com.banco.spider.integration.port;

import br.com.banco.spider.canonical.contract.CanonicalPayload;
import br.com.banco.spider.canonical.contract.TraceDescriptor;
import com.fasterxml.jackson.databind.JsonNode;
import java.time.Instant;
import java.util.Objects;

/**
 * Request universal Engine→Adapter — sem transporte HTTP/SOAP/fila.
 */
public record UniversalAdapterRequest(
    String protocolSchemaVersion,
    String protocolVersion,
    String invocationId,
    String executionId,
    String stepId,
    String attemptId,
    Instant invokedAt,
    String capabilityCode,
    String operationCode,
    String bindingRef,
    String inputContractRef,
    String outputContractRef,
    String errorContractRef,
    TraceDescriptor trace,
    Instant deadline,
    String idempotencyKey,
    CanonicalPayload payload) {

  public UniversalAdapterRequest {
    Objects.requireNonNull(invocationId, "invocationId");
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(stepId, "stepId");
    Objects.requireNonNull(attemptId, "attemptId");
    Objects.requireNonNull(invokedAt, "invokedAt");
    Objects.requireNonNull(capabilityCode, "capabilityCode");
    Objects.requireNonNull(operationCode, "operationCode");
    Objects.requireNonNull(bindingRef, "bindingRef");
    Objects.requireNonNull(trace, "trace");
    if (payload == null) {
      payload = CanonicalPayload.empty();
    }
    if (protocolSchemaVersion == null || protocolSchemaVersion.isBlank()) {
      protocolSchemaVersion = "1.0";
    }
    if (protocolVersion == null || protocolVersion.isBlank()) {
      protocolVersion = "1.0.0";
    }
  }

  public JsonNode canonicalData() {
    return payload.canonicalData();
  }

  public static Builder builder() {
    return new Builder();
  }

  public static final class Builder {
    private String protocolSchemaVersion = "1.0";
    private String protocolVersion = "1.0.0";
    private String invocationId;
    private String executionId;
    private String stepId;
    private String attemptId;
    private Instant invokedAt = Instant.now();
    private String capabilityCode;
    private String operationCode;
    private String bindingRef;
    private String inputContractRef;
    private String outputContractRef;
    private String errorContractRef;
    private TraceDescriptor trace;
    private Instant deadline;
    private String idempotencyKey;
    private CanonicalPayload payload = CanonicalPayload.empty();

    public Builder invocationId(String invocationId) {
      this.invocationId = invocationId;
      return this;
    }

    public Builder executionId(String executionId) {
      this.executionId = executionId;
      return this;
    }

    public Builder stepId(String stepId) {
      this.stepId = stepId;
      return this;
    }

    public Builder attemptId(String attemptId) {
      this.attemptId = attemptId;
      return this;
    }

    public Builder invokedAt(Instant invokedAt) {
      this.invokedAt = invokedAt;
      return this;
    }

    public Builder capabilityCode(String capabilityCode) {
      this.capabilityCode = capabilityCode;
      return this;
    }

    public Builder operationCode(String operationCode) {
      this.operationCode = operationCode;
      return this;
    }

    public Builder bindingRef(String bindingRef) {
      this.bindingRef = bindingRef;
      return this;
    }

    public Builder inputContractRef(String inputContractRef) {
      this.inputContractRef = inputContractRef;
      return this;
    }

    public Builder outputContractRef(String outputContractRef) {
      this.outputContractRef = outputContractRef;
      return this;
    }

    public Builder errorContractRef(String errorContractRef) {
      this.errorContractRef = errorContractRef;
      return this;
    }

    public Builder trace(TraceDescriptor trace) {
      this.trace = trace;
      return this;
    }

    public Builder deadline(Instant deadline) {
      this.deadline = deadline;
      return this;
    }

    public Builder idempotencyKey(String idempotencyKey) {
      this.idempotencyKey = idempotencyKey;
      return this;
    }

    public Builder payload(CanonicalPayload payload) {
      this.payload = payload;
      return this;
    }

    public UniversalAdapterRequest build() {
      return new UniversalAdapterRequest(
          protocolSchemaVersion,
          protocolVersion,
          invocationId,
          executionId,
          stepId,
          attemptId,
          invokedAt,
          capabilityCode,
          operationCode,
          bindingRef,
          inputContractRef,
          outputContractRef,
          errorContractRef,
          trace,
          deadline,
          idempotencyKey,
          payload);
    }
  }
}
