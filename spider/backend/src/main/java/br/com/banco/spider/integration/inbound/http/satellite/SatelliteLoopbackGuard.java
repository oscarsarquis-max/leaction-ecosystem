package br.com.banco.spider.integration.inbound.http.satellite;

import java.net.InetAddress;
import java.net.InetSocketAddress;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.web.server.ServerWebExchange;

public final class SatelliteLoopbackGuard {

  private SatelliteLoopbackGuard() {}

  public static boolean remoteForbidden(ServerWebExchange exchange, boolean loopbackOnly) {
    if (!loopbackOnly) {
      return false;
    }
    ServerHttpRequest request = exchange.getRequest();
    InetSocketAddress remote = request.getRemoteAddress();
    if (remote == null || remote.getAddress() == null) {
      return false;
    }
    InetAddress address = remote.getAddress();
    return !address.isLoopbackAddress() && !address.isAnyLocalAddress();
  }
}
