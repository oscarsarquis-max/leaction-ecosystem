package br.com.segsense.domain.consent;

public class InvalidCollectedValueException extends RuntimeException {

  public InvalidCollectedValueException() {
    super("invalid-collected-value");
  }
}
