package br.com.banco.spider.canonical.contract;

import java.util.Objects;

/** Descritor de versões do envelope e do contrato canônico. */
public record ContractDescriptor(String schemaVersion, String contractVersion) {

  public ContractDescriptor {
    Objects.requireNonNull(schemaVersion, "schemaVersion");
    Objects.requireNonNull(contractVersion, "contractVersion");
    schemaVersion = schemaVersion.trim();
    contractVersion = contractVersion.trim();
    if (schemaVersion.isEmpty() || contractVersion.isEmpty()) {
      throw new IllegalArgumentException("schemaVersion and contractVersion must not be blank");
    }
  }
}
