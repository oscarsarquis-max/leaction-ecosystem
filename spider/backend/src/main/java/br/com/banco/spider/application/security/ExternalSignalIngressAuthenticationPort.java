package br.com.banco.spider.application.security;

import br.com.banco.spider.execution.signal.SignalSecurityContext;
import java.util.Optional;
import reactor.core.publisher.Mono;

public interface ExternalSignalIngressAuthenticationPort {
  Mono<Optional<SignalSecurityContext>> authenticate(IngressAuthenticationRequest request);
}
