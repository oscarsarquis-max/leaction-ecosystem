package br.com.segsense.domain.link;

public class ContextLinkRevokedException extends RuntimeException {

  public ContextLinkRevokedException() {
    super("context-link-revoked");
  }
}
