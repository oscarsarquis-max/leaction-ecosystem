package br.com.banco.spider.security.context;

/**
 * Referência opaca à identidade do chamador autenticado.
 * Placeholder do incremento 001 — sem autenticação corporativa final.
 */
public record CallerIdentityRef(String identityRef, String authMethodRef) {

  public CallerIdentityRef {
    if (identityRef == null || identityRef.isBlank()) {
      throw new IllegalArgumentException("identityRef must not be blank");
    }
    identityRef = identityRef.trim();
    if (authMethodRef != null) {
      authMethodRef = authMethodRef.trim();
      if (authMethodRef.isEmpty()) {
        authMethodRef = null;
      }
    }
  }
}
