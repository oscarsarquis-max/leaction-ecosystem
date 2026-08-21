package br.com.banco.spider.execution.signal;

import reactor.core.publisher.Mono;

public interface ExternalSignalAuthorizationPort {
  Mono<Boolean> authorize(SignalSecurityContext context, String bindingRef, String securityProfileRef);
}
