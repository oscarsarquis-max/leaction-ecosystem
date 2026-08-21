package br.com.banco.spider.application.console;

import reactor.core.publisher.Mono;

public interface OperationalConsoleAuthenticationPort {
  Mono<OperationalConsoleSecurityContext> authenticate(String credentialRef);
}
