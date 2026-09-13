package br.com.segsense.domain.consent;

public class ContinuityUnavailableException extends RuntimeException {

  public ContinuityUnavailableException() {
    super("continuity-unavailable");
  }
}
