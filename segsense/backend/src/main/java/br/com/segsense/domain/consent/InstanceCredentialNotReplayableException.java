package br.com.segsense.domain.consent;

public class InstanceCredentialNotReplayableException extends RuntimeException {

  public InstanceCredentialNotReplayableException() {
    super("Instance credential cannot be replayed");
  }
}
