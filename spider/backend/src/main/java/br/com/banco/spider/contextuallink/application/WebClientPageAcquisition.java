package br.com.banco.spider.contextuallink.application;

import br.com.banco.spider.contextuallink.domain.AcquisitionUrlGuard;
import br.com.banco.spider.contextuallink.domain.AcquisitionUrlGuard.BlockedAcquisitionException;
import io.netty.channel.ChannelOption;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import org.springframework.http.HttpHeaders;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;
import reactor.netty.http.client.HttpClient;

public final class WebClientPageAcquisition implements PageAcquisitionPort {

  private static final int MAX_REDIRECTS = 2;

  private final WebClient client;
  private final AcquisitionUrlGuard guard;
  private final int maxBytes;
  private final Duration timeout;

  public WebClientPageAcquisition(
      WebClient.Builder builder, AcquisitionUrlGuard guard, int maxBytes, Duration timeout) {
    HttpClient httpClient =
        HttpClient.create()
            .followRedirect(false)
            .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, (int) Math.min(timeout.toMillis(), 3_000))
            .responseTimeout(timeout);
    this.client =
        builder.clone().clientConnector(new ReactorClientHttpConnector(httpClient)).build();
    this.guard = guard;
    this.maxBytes = maxBytes;
    this.timeout = timeout;
  }

  @Override
  public Mono<FetchedPage> fetch(URI uri) {
    URI start = guard.validate(uri.toString());
    return fetchHop(start, 0);
  }

  private Mono<FetchedPage> fetchHop(URI uri, int depth) {
    return client
        .get()
        .uri(uri)
        .exchangeToMono(
            response -> {
              if (response.statusCode().is3xxRedirection()) {
                if (depth >= MAX_REDIRECTS) {
                  return Mono.error(new BlockedAcquisitionException("too_many_redirects"));
                }
                String location = response.headers().asHttpHeaders().getFirst(HttpHeaders.LOCATION);
                URI next;
                try {
                  next = guard.validateRedirect(uri, location);
                } catch (BlockedAcquisitionException ex) {
                  return Mono.error(ex);
                }
                return response.releaseBody().then(fetchHop(next, depth + 1));
              }
              if (!response.statusCode().is2xxSuccessful()) {
                return response
                    .releaseBody()
                    .then(
                        Mono.error(
                            new IllegalStateException(
                                "acquisition_http_" + response.statusCode().value())));
              }
              return response
                  .bodyToMono(byte[].class)
                  .defaultIfEmpty(new byte[0])
                  .flatMap(
                      bytes -> {
                        if (bytes.length > maxBytes) {
                          return Mono.error(new BlockedAcquisitionException("payload_too_large"));
                        }
                        String body = new String(bytes, StandardCharsets.UTF_8);
                        return Mono.just(new FetchedPage(uri, body));
                      });
            })
        .timeout(timeout);
  }
}
