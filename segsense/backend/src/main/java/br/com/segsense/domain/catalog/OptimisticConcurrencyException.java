package br.com.segsense.domain.catalog;

public class OptimisticConcurrencyException extends RuntimeException {

  public OptimisticConcurrencyException() {
    super("concurrent-modification");
  }
}
