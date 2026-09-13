package br.com.segsense.domain.opportunity;

public class InvalidParentStateException extends RuntimeException {

  public InvalidParentStateException() {
    super("invalid-parent-state");
  }
}
