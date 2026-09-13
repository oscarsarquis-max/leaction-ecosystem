package br.com.segsense.domain.link;

public class ContextLinkNotFoundException extends RuntimeException {

  public ContextLinkNotFoundException() {
    super("context-link-not-found");
  }
}
