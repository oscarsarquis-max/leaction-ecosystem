package br.com.banco.spider.canonical.contract;

import java.util.Objects;

public record TraceDescriptor(String correlationId, String traceparent, String tracestate) {

  public TraceDescriptor {
    Objects.requireNonNull(correlationId, "correlationId");
    Objects.requireNonNull(traceparent, "traceparent");
    correlationId = correlationId.trim();
    traceparent = traceparent.trim();
    if (correlationId.isEmpty() || traceparent.isEmpty()) {
      throw new IllegalArgumentException("correlationId and traceparent must not be blank");
    }
    if (tracestate != null) {
      tracestate = tracestate.trim();
      if (tracestate.isEmpty()) {
        tracestate = null;
      }
    }
  }
}
