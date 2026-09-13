package br.com.segsense.domain.consent;

public class ConsentNoticeNotApprovedException extends RuntimeException {

  public ConsentNoticeNotApprovedException() {
    super("consent-notice-not-approved");
  }
}
