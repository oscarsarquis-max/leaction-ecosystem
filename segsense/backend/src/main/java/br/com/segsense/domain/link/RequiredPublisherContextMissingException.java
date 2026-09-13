package br.com.segsense.domain.link;

public class RequiredPublisherContextMissingException extends RuntimeException {

  public RequiredPublisherContextMissingException() {
    super("required-publisher-context-missing");
  }
}
