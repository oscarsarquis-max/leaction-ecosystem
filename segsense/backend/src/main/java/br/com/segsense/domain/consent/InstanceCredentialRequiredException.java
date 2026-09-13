package br.com.segsense.domain.consent;

public class InstanceCredentialRequiredException extends RuntimeException {

  public InstanceCredentialRequiredException() {
    super("instance-credential-required");
  }
}
