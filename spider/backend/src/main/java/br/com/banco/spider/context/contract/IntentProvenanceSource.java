package br.com.banco.spider.context.contract;

/**
 * Origem declarada da interpretação. NATURAL_LANGUAGE é reservado para etapa futura e não implica
 * que exista LLM no runtime atual.
 */
public enum IntentProvenanceSource {
  BUSINESS_CARD,
  FORM,
  API,
  NATURAL_LANGUAGE,
  EXTERNAL_PLATFORM,
  SERVICENOW
}
