package br.com.banco.spider.execution.mapping;

/** Mappings fechados e versionados — sem script/SpEL. */
public enum StepInputMappingKind {
  ROOT_REQUEST_CANONICAL_DATA,
  PREVIOUS_STEP_CANONICAL_DATA,
  MERGE_ROOT_AND_PREVIOUS_CANONICAL_DATA;

  public static final String REF_PREFIX = "mapping:";

  public String toRef() {
    return REF_PREFIX + name() + "@1.0";
  }

  public static StepInputMappingKind fromRef(String ref) {
    if (ref == null || ref.isBlank()) {
      throw new IllegalArgumentException("inputMappingRef is required");
    }
    String t = ref.trim();
    for (StepInputMappingKind k : values()) {
      if (t.equals(k.toRef()) || t.equals(k.name()) || t.equalsIgnoreCase(k.name())) {
        return k;
      }
    }
    throw new IllegalArgumentException("Unknown mapping ref: " + ref);
  }
}
