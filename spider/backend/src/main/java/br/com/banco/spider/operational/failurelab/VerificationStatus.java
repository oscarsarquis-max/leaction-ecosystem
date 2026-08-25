package br.com.banco.spider.operational.failurelab;

/** Resultado de uma observação esperada. Ausência de evidência nunca vira PASSED. */
public enum VerificationStatus {
  PASSED,
  FAILED,
  NOT_OBSERVED,
  NOT_APPLICABLE,
  INCONCLUSIVE
}
