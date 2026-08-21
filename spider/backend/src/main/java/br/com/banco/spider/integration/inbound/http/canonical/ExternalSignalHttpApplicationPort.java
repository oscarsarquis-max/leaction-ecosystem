package br.com.banco.spider.integration.inbound.http.canonical;

import br.com.banco.spider.execution.signal.ExternalSignalEnvelope;
import br.com.banco.spider.execution.signal.ExternalSignalProcessingResult;
import reactor.core.publisher.Mono;

/** Adapter inbound HTTP — não conhece JPA/crypto/processor. */
public interface ExternalSignalHttpApplicationPort {
  Mono<ExternalSignalProcessingResult> handle(ExternalSignalEnvelope envelope);
}
