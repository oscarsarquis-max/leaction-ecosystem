package br.com.banco.spider.canonical.contract;

import br.com.banco.spider.canonical.versioning.VersionedReference;
import java.util.Objects;

/**
 * Pedido canônico de execução — envelope técnico imutável (SPIDER-ARCH-003/004).
 * Não contém endpoint HTTP/SOAP/fila nem regra bancária.
 */
public record CanonicalExecutionRequest(
    ContractDescriptor contract,
    ExecutionIdentity execution,
    ContextReference contextRef,
    OriginDescriptor origin,
    TraceDescriptor trace,
    TargetDescriptor target,
    CanonicalPayload payload,
    ExecutionPolicyReference executionPolicy,
    VersionedReference callbackRef) {

  public CanonicalExecutionRequest {
    Objects.requireNonNull(contract, "contract");
    Objects.requireNonNull(execution, "execution");
    Objects.requireNonNull(contextRef, "contextRef");
    Objects.requireNonNull(origin, "origin");
    Objects.requireNonNull(trace, "trace");
    Objects.requireNonNull(target, "target");
    Objects.requireNonNull(payload, "payload");
    if (executionPolicy == null) {
      executionPolicy = ExecutionPolicyReference.empty();
    }
  }

  public static Builder builder() {
    return new Builder();
  }

  public static final class Builder {
    private ContractDescriptor contract;
    private ExecutionIdentity execution;
    private ContextReference contextRef;
    private OriginDescriptor origin;
    private TraceDescriptor trace;
    private TargetDescriptor target;
    private CanonicalPayload payload = CanonicalPayload.empty();
    private ExecutionPolicyReference executionPolicy = ExecutionPolicyReference.empty();
    private VersionedReference callbackRef;

    public Builder contract(ContractDescriptor contract) {
      this.contract = contract;
      return this;
    }

    public Builder execution(ExecutionIdentity execution) {
      this.execution = execution;
      return this;
    }

    public Builder contextRef(ContextReference contextRef) {
      this.contextRef = contextRef;
      return this;
    }

    public Builder origin(OriginDescriptor origin) {
      this.origin = origin;
      return this;
    }

    public Builder trace(TraceDescriptor trace) {
      this.trace = trace;
      return this;
    }

    public Builder target(TargetDescriptor target) {
      this.target = target;
      return this;
    }

    public Builder payload(CanonicalPayload payload) {
      this.payload = payload;
      return this;
    }

    public Builder executionPolicy(ExecutionPolicyReference executionPolicy) {
      this.executionPolicy = executionPolicy;
      return this;
    }

    public Builder callbackRef(VersionedReference callbackRef) {
      this.callbackRef = callbackRef;
      return this;
    }

    public CanonicalExecutionRequest build() {
      return new CanonicalExecutionRequest(
          contract,
          execution,
          contextRef,
          origin,
          trace,
          target,
          payload,
          executionPolicy,
          callbackRef);
    }
  }
}
