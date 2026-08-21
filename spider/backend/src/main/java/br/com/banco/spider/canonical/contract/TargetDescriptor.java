package br.com.banco.spider.canonical.contract;

import java.util.Objects;

/** Destino canônico — capability/operation apenas; sem endpoint físico. */
public record TargetDescriptor(String capability, String operation) {

  public TargetDescriptor {
    Objects.requireNonNull(capability, "capability");
    Objects.requireNonNull(operation, "operation");
    capability = capability.trim();
    operation = operation.trim();
    if (capability.isEmpty() || operation.isEmpty()) {
      throw new IllegalArgumentException("capability and operation must not be blank");
    }
  }
}
