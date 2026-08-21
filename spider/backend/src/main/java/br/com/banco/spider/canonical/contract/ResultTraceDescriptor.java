package br.com.banco.spider.canonical.contract;

import java.util.Objects;

public record ResultTraceDescriptor(String correlationId, String traceparent) {

  public ResultTraceDescriptor {
    Objects.requireNonNull(correlationId, "correlationId");
    Objects.requireNonNull(traceparent, "traceparent");
    correlationId = correlationId.trim();
    traceparent = traceparent.trim();
  }

  public static ResultTraceDescriptor from(TraceDescriptor trace) {
    return new ResultTraceDescriptor(trace.correlationId(), trace.traceparent());
  }
}
