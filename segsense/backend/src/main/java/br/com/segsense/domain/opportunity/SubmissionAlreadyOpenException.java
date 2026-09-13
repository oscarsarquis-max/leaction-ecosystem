package br.com.segsense.domain.opportunity;

public class SubmissionAlreadyOpenException extends RuntimeException {

  public SubmissionAlreadyOpenException() {
    super("submission-already-open");
  }
}
