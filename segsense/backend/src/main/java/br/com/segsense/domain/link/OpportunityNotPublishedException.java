package br.com.segsense.domain.link;

public class OpportunityNotPublishedException extends RuntimeException {

  public OpportunityNotPublishedException() {
    super("opportunity-not-published");
  }
}
