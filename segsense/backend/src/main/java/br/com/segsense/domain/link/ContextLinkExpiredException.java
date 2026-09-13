package br.com.segsense.domain.link;

public class ContextLinkExpiredException extends RuntimeException {

  public ContextLinkExpiredException() {
    super("context-link-expired");
  }
}
