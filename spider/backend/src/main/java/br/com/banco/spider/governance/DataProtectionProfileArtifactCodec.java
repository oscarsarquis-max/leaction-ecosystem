package br.com.banco.spider.governance;

import br.com.banco.spider.security.dataprotection.DataProtectionProfileDefinition;

/** Codec tipado do artifact DATA_PROTECTION_PROFILE (JSON fechado via registry). */
public final class DataProtectionProfileArtifactCodec {

  private DataProtectionProfileArtifactCodec() {}

  public static Class<DataProtectionProfileDefinition> domainClass() {
    return DataProtectionProfileDefinition.class;
  }
}
