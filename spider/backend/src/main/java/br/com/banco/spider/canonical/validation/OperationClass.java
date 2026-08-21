package br.com.banco.spider.canonical.validation;

/** Classificação da operação para regras condicionais (ex.: idempotencyKey). */
public enum OperationClass {
  /** Leitura / consulta sem efeito colateral esperado. */
  QUERY,
  /** Operação com efeito — exige idempotencyKey neste incremento. */
  EFFECT
}
