package br.com.banco.spider.contextuallink.domain;

import java.time.Instant;
import java.util.Objects;

public record ProvenanceStep(
    int order,
    String code,
    String label,
    Instant occurredAt,
    String status,
    String detail) {

  public ProvenanceStep {
    Objects.requireNonNull(code, "code");
    Objects.requireNonNull(label, "label");
    Objects.requireNonNull(occurredAt, "occurredAt");
    Objects.requireNonNull(status, "status");
    detail = detail == null ? "" : detail;
  }
}
