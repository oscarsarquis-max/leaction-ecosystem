package br.com.banco.spider.context.domain;

public enum ContextGuardDecision {
  ACCEPTED,
  MISSING_CONTEXT,
  AMBIGUOUS,
  NOT_AUTHORIZED,
  POLICY_REJECTED,
  UNSUPPORTED_INTENT
}
