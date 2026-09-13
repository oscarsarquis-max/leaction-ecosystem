package br.com.segsense.domain.consent;

public class InvalidIdempotencyKeyException extends RuntimeException {

  public InvalidIdempotencyKeyException() {
    super("Idempotency-Key is invalid");
  }
}
