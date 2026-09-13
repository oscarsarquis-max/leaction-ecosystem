package br.com.segsense.domain.consent;

public class ContextInstanceUnauthorizedException extends RuntimeException {

  public ContextInstanceUnauthorizedException() {
    super("context-instance-unauthorized");
  }
}
