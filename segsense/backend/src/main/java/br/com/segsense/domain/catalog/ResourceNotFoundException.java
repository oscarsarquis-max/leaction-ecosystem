package br.com.segsense.domain.catalog;

public class ResourceNotFoundException extends RuntimeException {

  public ResourceNotFoundException() {
    super("not-found");
  }
}
