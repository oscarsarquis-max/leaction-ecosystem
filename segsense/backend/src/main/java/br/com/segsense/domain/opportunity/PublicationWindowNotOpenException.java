package br.com.segsense.domain.opportunity;

public class PublicationWindowNotOpenException extends RuntimeException {

  public PublicationWindowNotOpenException() {
    super("publication-window-not-open");
  }
}
