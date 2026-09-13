package br.com.segsense.domain.consent;

public class ContextInstanceExpiredException extends RuntimeException {

  public ContextInstanceExpiredException() {
    super("context-instance-expired");
  }
}
