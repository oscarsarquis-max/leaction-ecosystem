package br.com.banco.spider.contextuallink.application;

import java.net.URI;
import reactor.core.publisher.Mono;

public interface PageAcquisitionPort {

  Mono<FetchedPage> fetch(URI uri);

  record FetchedPage(URI finalUri, String body) {}
}
