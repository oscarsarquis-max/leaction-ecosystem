package br.com.banco.spider.application.security;

import java.util.Optional;
import reactor.core.publisher.Mono;

public interface CanonicalIngressAuthenticationPort {
  Mono<Optional<AuthenticatedOriginator>> authenticate(IngressAuthenticationRequest request);
}
