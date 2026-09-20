package br.com.banco.spider.satellite.application;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.HexFormat;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * Local-demo HMAC assertion of a synthetic customer. Not KYC and not a real IdP token.
 */
public final class DemoCustomerAssertion {

  public static final Set<String> REGISTERED_SUBJECTS =
      Set.of(
          "cust-demo-ok",
          "cust-demo-pending-registration",
          "cust-demo-no-profile",
          "cust-demo-ineligible",
          "cust-demo-rejected",
          "cust-demo-review");

  private static final Pattern TOKEN =
      Pattern.compile("v1\\.([A-Za-z0-9_-]+)\\.(cust-demo-[a-z0-9-]+)\\.(\\d+)\\.(\\d+)\\.([A-Fa-f0-9]{32,})");

  private DemoCustomerAssertion() {}

  public static String issue(String secret, String satelliteId, String subjectRef, Instant issuedAt, Instant expiresAt) {
    if (secret == null || secret.length() < 16) {
      throw new IllegalStateException("Segredo de afirmação demonstrativa ausente.");
    }
    if (!REGISTERED_SUBJECTS.contains(subjectRef)) {
      throw new IllegalArgumentException("Sujeito sintético não registrado.");
    }
    String payload =
        "v1." + satelliteId + "." + subjectRef + "." + issuedAt.getEpochSecond() + "." + expiresAt.getEpochSecond();
    return payload + "." + hmac(secret, payload);
  }

  public static Verified verify(String secret, String satelliteId, String token) {
    if (secret == null || secret.length() < 16 || token == null || token.isBlank()) {
      return null;
    }
    Matcher matcher = TOKEN.matcher(token);
    if (!matcher.matches()) {
      return null;
    }
    String claimedSatellite = matcher.group(1);
    String subject = matcher.group(2);
    long issued = Long.parseLong(matcher.group(3));
    long expires = Long.parseLong(matcher.group(4));
    String signature = matcher.group(5);
    if (!satelliteId.equals(claimedSatellite) || !REGISTERED_SUBJECTS.contains(subject)) {
      return null;
    }
    Instant now = Instant.now();
    if (expires <= issued
        || Instant.ofEpochSecond(expires).isBefore(now)
        || Instant.ofEpochSecond(issued).isAfter(now.plusSeconds(5))) {
      return null;
    }
    String payload = "v1." + claimedSatellite + "." + subject + "." + issued + "." + expires;
    if (!MessageDigest.isEqual(bytes(hmac(secret, payload)), bytes(signature))) {
      return null;
    }
    return new Verified(subject, Instant.ofEpochSecond(issued), Instant.ofEpochSecond(expires));
  }

  private static byte[] bytes(String hex) {
    return HexFormat.of().parseHex(hex);
  }

  private static String hmac(String secret, String payload) {
    try {
      Mac mac = Mac.getInstance("HmacSHA256");
      mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
      return HexFormat.of().formatHex(mac.doFinal(payload.getBytes(StandardCharsets.UTF_8)));
    } catch (Exception e) {
      throw new IllegalStateException(e);
    }
  }

  public record Verified(String subjectRef, Instant issuedAt, Instant expiresAt) {}
}
