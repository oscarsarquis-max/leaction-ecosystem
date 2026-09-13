package br.com.segsense.domain.link;

public class ApprovedRevisionMismatchException extends RuntimeException {

  public ApprovedRevisionMismatchException() {
    super("approved-revision-mismatch");
  }
}
