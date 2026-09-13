package br.com.segsense.domain.link;

public class ContextLinkUnavailableException extends RuntimeException {

  public ContextLinkUnavailableException() {
    super("context-link-unavailable");
  }
}
