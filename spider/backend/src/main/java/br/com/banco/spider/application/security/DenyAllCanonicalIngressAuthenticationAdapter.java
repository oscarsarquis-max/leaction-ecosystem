package br.com.banco.spider.application.security;

import java.util.Optional;
import reactor.core.publisher.Mono;

/** Default seguro — nunca permite acesso no runtime normal. */
public class DenyAllCanonicalIngressAuthenticationAdapter
    implements CanonicalIngressAuthenticationPort {

  @Override
  public Mono<Optional<AuthenticatedOriginator>> authenticate(IngressAuthenticationRequest request) {
    return Mono.just(Optional.empty());
  }
}
