package br.com.banco.spider.execution.signal;

public enum ExternalSignalInputMappingKind {
  STATUS_ONLY_V1,
  RESULT_DATA_V1,
  MERGE_WITH_WAIT_CONTEXT_V1;

  public static ExternalSignalInputMappingKind fromRef(String ref) {
    if (ref == null || ref.isBlank()) {
      return STATUS_ONLY_V1;
    }
    String n = ref.trim();
    for (ExternalSignalInputMappingKind k : values()) {
      if (k.name().equals(n) || ("mapping:signal:" + k.name()).equalsIgnoreCase(n)) {
        return k;
      }
    }
    throw new IllegalArgumentException("UNKNOWN_SIGNAL_MAPPING:" + n);
  }
}
