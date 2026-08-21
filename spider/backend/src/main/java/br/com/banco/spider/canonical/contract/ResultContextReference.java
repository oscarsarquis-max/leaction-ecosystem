package br.com.banco.spider.canonical.contract;

import java.util.Objects;

/** Subconjunto de contexto no resultado. */
public record ResultContextReference(
    String contextId, String intentId, String capabilityId, String journeyId) {

  public ResultContextReference {
    contextId = req("contextId", contextId);
    intentId = req("intentId", intentId);
    capabilityId = req("capabilityId", capabilityId);
    journeyId = req("journeyId", journeyId);
  }

  private static String req(String name, String value) {
    Objects.requireNonNull(value, name);
    String t = value.trim();
    if (t.isEmpty()) {
      throw new IllegalArgumentException(name + " must not be blank");
    }
    return t;
  }

  public static ResultContextReference from(ContextReference ctx) {
    return new ResultContextReference(
        ctx.contextId(), ctx.intentId(), ctx.capabilityId(), ctx.journeyId());
  }
}
