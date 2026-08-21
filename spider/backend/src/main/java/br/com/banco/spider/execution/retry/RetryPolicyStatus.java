package br.com.banco.spider.execution.retry;

public enum RetryPolicyStatus {
  DRAFT,
  PUBLISHED,
  DEPRECATED,
  RETIRED;

  public boolean isEligible() {
    return this == PUBLISHED;
  }
}
