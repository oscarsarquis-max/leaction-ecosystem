package br.com.segsense.domain.opportunity;

public class InvalidGovernanceTransitionException extends RuntimeException {

  public InvalidGovernanceTransitionException() {
    super("invalid-governance-transition");
  }
}
