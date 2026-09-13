package br.com.segsense.domain.catalog;

public class DuplicateResourceKeyException extends RuntimeException {

  private final String code;

  public DuplicateResourceKeyException(String code, String message) {
    super(message);
    this.code = code;
  }

  public String code() {
    return code;
  }
}
