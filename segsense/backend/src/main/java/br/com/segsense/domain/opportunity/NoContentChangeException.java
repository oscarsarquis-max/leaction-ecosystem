package br.com.segsense.domain.opportunity;

public class NoContentChangeException extends RuntimeException {

  public NoContentChangeException() {
    super("no-content-change");
  }
}
