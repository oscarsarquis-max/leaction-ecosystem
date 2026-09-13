package br.com.segsense.domain.opportunity;

public class JustificationRequiredException extends RuntimeException {

  public JustificationRequiredException() {
    super("justification-required");
  }
}
