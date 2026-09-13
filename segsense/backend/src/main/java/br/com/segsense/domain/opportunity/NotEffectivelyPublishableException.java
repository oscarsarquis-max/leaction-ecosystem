package br.com.segsense.domain.opportunity;

public class NotEffectivelyPublishableException extends RuntimeException {

  public NotEffectivelyPublishableException() {
    super("not-effectively-publishable");
  }
}
