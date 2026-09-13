package br.com.segsense.domain.consent;

public class IdempotencyKeyRequiredException extends RuntimeException {

  public IdempotencyKeyRequiredException() {
    super("Idempotency-Key is required");
  }
}
