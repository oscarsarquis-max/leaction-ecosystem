package br.com.banco.spider.web.filter;

import java.security.SecureRandom;
import java.util.HexFormat;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilter;
import org.springframework.web.server.WebFilterChain;
import reactor.core.publisher.Mono;
import reactor.util.context.Context;

/**
 * Intercepta todas as requisições e propaga W3C Trace Context ({@code traceparent}).
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class TraceContextWebFilter implements WebFilter {

  public static final String TRACEPARENT_HEADER = "traceparent";
  public static final String CONTEXT_KEY = "traceparent";

  private static final Logger log = LoggerFactory.getLogger(TraceContextWebFilter.class);
  private static final SecureRandom RANDOM = new SecureRandom();
  private static final HexFormat HEX = HexFormat.of();

  @Override
  public Mono<Void> filter(ServerWebExchange exchange, WebFilterChain chain) {
    ServerHttpRequest request = exchange.getRequest();
    String incoming = request.getHeaders().getFirst(TRACEPARENT_HEADER);
    String traceparent = isValidTraceparent(incoming) ? incoming.trim() : generateTraceparent();

    ServerWebExchange mutated =
        exchange
            .mutate()
            .request(builder -> builder.header(TRACEPARENT_HEADER, traceparent))
            .build();
    mutated.getResponse().getHeaders().set(TRACEPARENT_HEADER, traceparent);

    return chain
        .filter(mutated)
        .contextWrite(Context.of(CONTEXT_KEY, traceparent))
        .doOnEach(
            signal -> {
              if (signal.isOnNext() || signal.isOnComplete() || signal.isOnError()) {
                signal
                    .getContextView()
                    .getOrEmpty(CONTEXT_KEY)
                    .ifPresent(tp -> MDC.put(CONTEXT_KEY, String.valueOf(tp)));
              }
            })
        .doFinally(st -> MDC.remove(CONTEXT_KEY))
        .doOnSubscribe(s -> {
          MDC.put(CONTEXT_KEY, traceparent);
          log.debug("Trace context bound path={} traceparent={}", request.getPath(), traceparent);
        });
  }

  static boolean isValidTraceparent(String value) {
    if (value == null || value.isBlank()) {
      return false;
    }
    // version(2)-traceid(32)-parentid(16)-flags(2) hex, hyphen-separated
    String[] parts = value.trim().split("-");
    if (parts.length != 4) {
      return false;
    }
    return parts[0].length() == 2
        && parts[1].length() == 32
        && parts[2].length() == 16
        && parts[3].length() == 2
        && parts[1].chars().allMatch(c -> Character.digit(c, 16) >= 0)
        && !parts[1].chars().allMatch(c -> c == '0');
  }

  public static String generateTraceparent() {
    byte[] traceId = new byte[16];
    byte[] parentId = new byte[8];
    RANDOM.nextBytes(traceId);
    RANDOM.nextBytes(parentId);
    // avoid all-zero ids
    if (isAllZero(traceId)) {
      traceId[0] = 1;
    }
    if (isAllZero(parentId)) {
      parentId[0] = 1;
    }
    return "00-" + HEX.formatHex(traceId) + "-" + HEX.formatHex(parentId) + "-01";
  }

  private static boolean isAllZero(byte[] bytes) {
    for (byte b : bytes) {
      if (b != 0) {
        return false;
      }
    }
    return true;
  }
}
