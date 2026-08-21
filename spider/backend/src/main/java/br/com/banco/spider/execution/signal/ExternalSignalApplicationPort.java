package br.com.banco.spider.execution.signal;

import reactor.core.publisher.Mono;

public interface ExternalSignalApplicationPort {
  Mono<ExternalSignalProcessingResult> process(ExternalSignalEnvelope signal);
}
