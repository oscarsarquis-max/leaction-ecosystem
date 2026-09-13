package br.com.segsense.domain.link;

public class ContextLinkTemporarilyUnavailableException extends RuntimeException {

  public static final int RETRY_AFTER_SECONDS = 60;

  public ContextLinkTemporarilyUnavailableException() {
    super("context-link-temporarily-unavailable");
  }

  public int retryAfterSeconds() {
    return RETRY_AFTER_SECONDS;
  }
}
