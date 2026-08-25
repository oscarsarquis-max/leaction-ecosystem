package br.com.banco.spider.operational.failurelab;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Redação conservadora do Failure Lab: chaves sensíveis nunca saem do processo e qualquer texto
 * suspeito de credencial é bloqueado antes de virar evidência.
 */
public final class FailureLabRedaction {

  private static final int MAX_VALUE_LENGTH = 200;

  private static final List<String> SENSITIVE_TOKENS =
      List.of(
          "token",
          "secret",
          "password",
          "senha",
          "hmac",
          "nonce",
          "ciphertext",
          "cipher",
          "credential",
          "authorization",
          "bearer",
          "jwt",
          "signature",
          "apikey",
          "api-key",
          "privatekey",
          "private-key");

  private FailureLabRedaction() {}

  /** Remove chaves sensíveis e trunca valores. Chaves com valor suspeito também são descartadas. */
  public static Map<String, String> sanitize(Map<String, String> input) {
    if (input == null || input.isEmpty()) {
      return Map.of();
    }
    Map<String, String> clean = new LinkedHashMap<>();
    input.forEach(
        (key, value) -> {
          if (key == null || value == null) {
            return;
          }
          if (looksSensitive(key) || looksSensitive(value)) {
            return;
          }
          clean.put(
              key,
              value.length() > MAX_VALUE_LENGTH ? value.substring(0, MAX_VALUE_LENGTH) : value);
        });
    return Map.copyOf(clean);
  }

  public static boolean looksSensitive(String value) {
    if (value == null || value.isBlank()) {
      return false;
    }
    String normalized = value.toLowerCase(Locale.ROOT);
    for (String marker : SENSITIVE_TOKENS) {
      if (normalized.contains(marker)) {
        return true;
      }
    }
    return false;
  }

  /** Mensagem segura para exposição: apenas código estável, sem detalhe técnico livre. */
  public static String safeReason(String reasonCode) {
    if (reasonCode == null || reasonCode.isBlank()) {
      return "UNSPECIFIED";
    }
    String normalized = reasonCode.trim().toUpperCase(Locale.ROOT).replaceAll("[^A-Z0-9_]", "_");
    return normalized.length() > 64 ? normalized.substring(0, 64) : normalized;
  }
}
