package br.com.segsense.domain.link;

public class LinkExpiryInvalidException extends RuntimeException {

  public LinkExpiryInvalidException() {
    super("link-expiry-invalid");
  }
}
