package br.com.segsense.domain.demo;

public class DemoProtectionException extends RuntimeException {

  private final String code;
  private final int httpStatus;

  public DemoProtectionException(String code, int httpStatus, String message) {
    super(message);
    this.code = code;
    this.httpStatus = httpStatus;
  }

  public String code() {
    return code;
  }

  public int httpStatus() {
    return httpStatus;
  }
}
