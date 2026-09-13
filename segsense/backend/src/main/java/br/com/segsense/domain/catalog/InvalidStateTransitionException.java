package br.com.segsense.domain.catalog;

public class InvalidStateTransitionException extends RuntimeException {

  public InvalidStateTransitionException() {
    super("invalid-state-transition");
  }
}
