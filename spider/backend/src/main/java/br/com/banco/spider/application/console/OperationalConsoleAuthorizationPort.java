package br.com.banco.spider.application.console;

import reactor.core.publisher.Mono;

public interface OperationalConsoleAuthorizationPort {
  Mono<Boolean> authorize(OperationalConsoleSecurityContext ctx, OperationalConsoleAction action);
}
