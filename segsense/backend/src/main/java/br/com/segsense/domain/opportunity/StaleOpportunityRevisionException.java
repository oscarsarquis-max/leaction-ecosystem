package br.com.segsense.domain.opportunity;

public class StaleOpportunityRevisionException extends RuntimeException {

  public StaleOpportunityRevisionException() {
    super("stale-opportunity-revision");
  }
}
