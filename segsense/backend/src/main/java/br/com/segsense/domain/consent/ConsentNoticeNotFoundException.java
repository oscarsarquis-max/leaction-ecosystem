package br.com.segsense.domain.consent;

public class ConsentNoticeNotFoundException extends RuntimeException {

  public ConsentNoticeNotFoundException() {
    super("consent-notice-not-found");
  }
}
