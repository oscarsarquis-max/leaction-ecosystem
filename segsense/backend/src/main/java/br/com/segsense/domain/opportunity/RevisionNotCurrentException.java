package br.com.segsense.domain.opportunity;

public class RevisionNotCurrentException extends RuntimeException {

  public RevisionNotCurrentException() {
    super("revision-not-current");
  }
}
