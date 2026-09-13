package br.com.segsense.domain.opportunity;

public class PublicationNotExpiredException extends RuntimeException {

  public PublicationNotExpiredException() {
    super("publication-not-expired");
  }
}
