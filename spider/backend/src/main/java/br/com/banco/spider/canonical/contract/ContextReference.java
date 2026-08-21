package br.com.banco.spider.canonical.contract;

import java.util.Objects;

/** Referências contextuais opacas/versionadas (não são SoR). */
public record ContextReference(
    String contextId,
    String intentId,
    String capabilityId,
    String productServiceId,
    String journeyId) {

  public ContextReference {
    contextId = requireOpaque("contextId", contextId);
    intentId = requireOpaque("intentId", intentId);
    capabilityId = requireOpaque("capabilityId", capabilityId);
    productServiceId = requireOpaque("productServiceId", productServiceId);
    journeyId = requireOpaque("journeyId", journeyId);
  }

  private static String requireOpaque(String name, String value) {
    Objects.requireNonNull(value, name);
    String t = value.trim();
    if (t.isEmpty()) {
      throw new IllegalArgumentException(name + " must not be blank");
    }
    return t;
  }
}
