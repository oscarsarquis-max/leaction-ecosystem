package br.com.segsense.domain.consent;

public class ConsentNoticeObsoleteException extends RuntimeException {

  public ConsentNoticeObsoleteException() {
    super("consent-notice-obsolete");
  }
}
