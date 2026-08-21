package br.com.banco.spider.application.security;

import br.com.banco.spider.execution.signal.SignalSecurityContext;
import java.util.Optional;
import reactor.core.publisher.Mono;

public class DenyAllExternalSignalIngressAuthenticationAdapter
    implements ExternalSignalIngressAuthenticationPort {

  @Override
  public Mono<Optional<SignalSecurityContext>> authenticate(IngressAuthenticationRequest request) {
    return Mono.just(Optional.empty());
  }
}
