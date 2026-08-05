package br.com.banco.spider.engine;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;
import javax.crypto.SecretKey;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class JwtTokenService {

  private final SecretKey key;
  private final String issuer;
  private final long ttlSeconds;

  public JwtTokenService(
      @Value("${spider.jwt.secret}") String secret,
      @Value("${spider.jwt.issuer:leaction-spider}") String issuer,
      @Value("${spider.jwt.ttl-seconds:300}") long ttlSeconds) {
    byte[] bytes = secret.getBytes(StandardCharsets.UTF_8);
    if (bytes.length < 32) {
      // HS256 requires >= 256-bit key material
      byte[] padded = new byte[32];
      System.arraycopy(bytes, 0, padded, 0, Math.min(bytes.length, 32));
      bytes = padded;
    }
    this.key = Keys.hmacShaKeyFor(bytes);
    this.issuer = issuer;
    this.ttlSeconds = ttlSeconds;
  }

  /**
   * Emite JWT de transição de estado (claims técnicas apenas).
   *
   * @param status técnico: {@code PAYMENT_CONFIRMED} ou {@code SUCCESS}
   */
  public String generateStateTransitionToken(String traceId, String productId, String status) {
    Instant now = Instant.now();
    String technicalStatus =
        "PAYMENT_CONFIRMED".equalsIgnoreCase(status) ? "PAYMENT_CONFIRMED" : "SUCCESS";

    return Jwts.builder()
        .issuer(issuer)
        .subject(traceId)
        .claim("product_id", productId)
        .claim("status_tecnico", technicalStatus)
        .claim("traceparent", traceId.startsWith("00-") ? traceId : null)
        .issuedAt(Date.from(now))
        .expiration(Date.from(now.plusSeconds(ttlSeconds)))
        .signWith(key, Jwts.SIG.HS256)
        .compact();
  }

  /** Variante com traceparent completo no claim dedicado. */
  public String generateStateTransitionToken(
      String transactionId, String productId, String status, String traceparent) {
    Instant now = Instant.now();
    String technicalStatus =
        "PAYMENT_CONFIRMED".equalsIgnoreCase(status) ? "PAYMENT_CONFIRMED" : "SUCCESS";

    return Jwts.builder()
        .issuer(issuer)
        .subject(transactionId)
        .claim("product_id", productId)
        .claim("status_tecnico", technicalStatus)
        .claim("traceparent", traceparent)
        .issuedAt(Date.from(now))
        .expiration(Date.from(now.plusSeconds(ttlSeconds)))
        .signWith(key, Jwts.SIG.HS256)
        .compact();
  }
}
