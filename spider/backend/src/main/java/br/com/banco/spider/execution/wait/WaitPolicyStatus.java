package br.com.banco.spider.execution.wait;

public enum WaitPolicyStatus {
  DRAFT,
  PUBLISHED,
  DEPRECATED,
  RETIRED;

  public boolean isEligible() {
    return this == PUBLISHED;
  }
}
