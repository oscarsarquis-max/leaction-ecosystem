package br.com.spiderbank.application;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class DemoCustomerSessionService {

  private static final Map<String, String> PERSONAS =
      Map.of(
          "ok", "cust-demo-ok",
          "pending-registration", "cust-demo-pending-registration",
          "no-profile", "cust-demo-no-profile",
          "ineligible", "cust-demo-ineligible",
          "rejected", "cust-demo-rejected",
          "review", "cust-demo-review");

  private static final Set<String> SUBJECTS = Set.copyOf(PERSONAS.values());

  private final String secret;

  public DemoCustomerSessionService(
      @Value("${spiderbank.customer-assertion.secret:}") String secret) {
    this.secret = secret == null ? "" : secret;
  }

  public Map<String, Object> start(String persona) {
    if (secret.length() < 16) {
      throw new CreditJourneyException(
          "TECHNICAL_UNAVAILABLE",
          503,
          "A sessão demonstrativa não está configurada neste ambiente.");
    }
    String key = persona == null || persona.isBlank() ? "ok" : persona;
    String subject = PERSONAS.get(key);
    if (subject == null) {
      throw new CreditJourneyException("VALIDATION_ERROR", 400, "Persona demonstrativa desconhecida.");
    }
    Instant issued = Instant.now();
    Instant expires = issued.plusSeconds(30 * 60);
    String token = issue("spiderbank", subject, issued, expires);
    Map<String, Object> view = new LinkedHashMap<>();
    view.put("environment", "TEST_DOUBLE");
    view.put("synthetic", true);
    view.put("label", "Cliente sintético de teste");
    view.put("persona", key);
    view.put("subjectRef", subject);
    view.put("assertion", token);
    view.put("expiresAt", expires.toString());
    view.put("warning", "Sessão demonstrativa. Não é autenticação de cliente real, KYC nem provedor de identidade.");
    return view;
  }

  public String requireAssertion(String token) {
    if (token == null || token.isBlank()) {
      return null;
    }
    if (secret.length() < 16 || !valid(token)) {
      throw new CreditJourneyException("VALIDATION_ERROR", 400, "A afirmação de cliente sintético é inválida ou expirou.");
    }
    return token;
  }

  private boolean valid(String token) {
    String[] parts = token.split("\\.");
    if (parts.length != 6 || !"v1".equals(parts[0]) || !"spiderbank".equals(parts[1]) || !SUBJECTS.contains(parts[2])) {
      return false;
    }
    String payload = "v1." + parts[1] + "." + parts[2] + "." + parts[3] + "." + parts[4];
    return hmac(payload).equalsIgnoreCase(parts[5]);
  }

  private String issue(String satelliteId, String subjectRef, Instant issuedAt, Instant expiresAt) {
    String payload = "v1." + satelliteId + "." + subjectRef + "." + issuedAt.getEpochSecond() + "." + expiresAt.getEpochSecond();
    return payload + "." + hmac(payload);
  }

  private String hmac(String payload) {
    try {
      Mac mac = Mac.getInstance("HmacSHA256");
      mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
      return HexFormat.of().formatHex(mac.doFinal(payload.getBytes(StandardCharsets.UTF_8)));
    } catch (Exception e) {
      throw new IllegalStateException(e);
    }
  }
}
