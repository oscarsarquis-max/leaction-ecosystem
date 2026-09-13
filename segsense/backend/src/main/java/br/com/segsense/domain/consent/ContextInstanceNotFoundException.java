package br.com.segsense.domain.consent;

public class ContextInstanceNotFoundException extends RuntimeException {

  public ContextInstanceNotFoundException() {
    super("context-instance-not-found");
  }
}
