package br.com.spiderbank.application;

public final class CreditJourneyException extends RuntimeException {

  private final String errorCode;
  private final int status;
  private final boolean retryable;

  public CreditJourneyException(String errorCode, int status, String message) {
    this(errorCode, status, message, false);
  }

  public CreditJourneyException(String errorCode, int status, String message, boolean retryable) {
    super(message);
    this.errorCode = errorCode;
    this.status = status;
    this.retryable = retryable;
  }

  public String errorCode() {
    return errorCode;
  }

  public int status() {
    return status;
  }

  public boolean retryable() {
    return retryable;
  }
}
