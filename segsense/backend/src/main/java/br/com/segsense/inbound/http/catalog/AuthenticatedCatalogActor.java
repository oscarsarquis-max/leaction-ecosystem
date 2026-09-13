package br.com.segsense.inbound.http.catalog;

import br.com.segsense.application.catalog.CatalogActor;
import org.springframework.security.core.Authentication;

public final class AuthenticatedCatalogActor {

  private AuthenticatedCatalogActor() {}

  public static CatalogActor from(Authentication authentication) {
    if (authentication == null
        || !authentication.isAuthenticated()
        || authentication.getName() == null
        || authentication.getName().isBlank()
        || "anonymousUser".equals(authentication.getName())) {
      throw new IllegalStateException("authenticated actor required");
    }
    return new CatalogActor(authentication.getName());
  }
}
