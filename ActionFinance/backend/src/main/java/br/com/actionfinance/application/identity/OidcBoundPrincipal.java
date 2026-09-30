package br.com.actionfinance.application.identity;

import br.com.actionfinance.application.ApplicationPrincipal;

public interface OidcBoundPrincipal extends ApplicationPrincipal {

    String issuer();

    String subject();
}
