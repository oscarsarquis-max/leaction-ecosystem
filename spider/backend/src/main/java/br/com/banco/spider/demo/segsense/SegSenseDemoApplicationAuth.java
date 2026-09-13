package br.com.banco.spider.demo.segsense;

import br.com.banco.spider.config.SegSenseDemoProperties;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.web.server.ServerWebExchange;

public final class SegSenseDemoApplicationAuth {

  public static final String SECRET_HEADER = "X-SEGSENSE-Demo-Application-Secret";

  private final SegSenseDemoProperties properties;

  public SegSenseDemoApplicationAuth(SegSenseDemoProperties properties) {
    this.properties = properties;
  }

  public boolean remoteForbidden(ServerWebExchange exchange) {
    ServerHttpRequest request = exchange.getRequest();
    InetSocketAddress remote = request.getRemoteAddress();
    if (remote == null || remote.getAddress() == null) {
      return false;
    }
    InetAddress address = remote.getAddress();
    return !address.isLoopbackAddress() && !address.isAnyLocalAddress();
  }

  public boolean authenticated(String credentialRef, String providedSecret) {
    String expected = properties.getApplicationSecret();
    if (expected == null || expected.isBlank()) {
      return false;
    }
    if (!properties.getCredentialRef().equals(credentialRef)) {
      return false;
    }
    return MessageDigest.isEqual(sha256(expected), sha256(providedSecret == null ? "" : providedSecret));
  }

  private static byte[] sha256(String value) {
    try {
      return MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
    } catch (NoSuchAlgorithmException e) {
      throw new IllegalStateException(e);
    }
  }
}
