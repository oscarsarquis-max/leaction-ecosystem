package br.com.segsense.application.urlcapture;

public final class UrlCaptureRejectedException extends RuntimeException {

  private final String resultCode;

  public UrlCaptureRejectedException(String resultCode, String publicMessage) {
    super(publicMessage);
    this.resultCode = resultCode;
  }

  public String resultCode() {
    return resultCode;
  }
}
