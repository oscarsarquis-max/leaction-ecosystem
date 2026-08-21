package br.com.banco.spider.governance;

public record GovernanceApprovalPolicy(
    boolean requireDistinctPublisher, boolean requireDistinctActivator) {

  public static GovernanceApprovalPolicy conservative() {
    return new GovernanceApprovalPolicy(true, true);
  }
}
