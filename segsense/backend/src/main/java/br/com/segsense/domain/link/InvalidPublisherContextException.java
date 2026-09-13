package br.com.segsense.domain.link;

public class InvalidPublisherContextException extends RuntimeException {

  public InvalidPublisherContextException() {
    super("invalid-publisher-context");
  }
}
