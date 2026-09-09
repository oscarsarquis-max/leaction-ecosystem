package br.com.banco.spider.contextuallink.domain;

import com.fasterxml.jackson.annotation.JsonInclude;
import java.util.Objects;

/** DEMO-001 materializa somente clickId e contextId. Os demais ficam nulos até incrementos futuros. */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record CorrelationChain(
    String clickId,
    String contextId,
    String decisionId,
    String planId,
    String executionId) {

  public CorrelationChain {
    Objects.requireNonNull(clickId, "clickId");
    Objects.requireNonNull(contextId, "contextId");
  }

  public static CorrelationChain of(String clickId, String contextId) {
    return new CorrelationChain(clickId, contextId, null, null, null);
  }

  public CorrelationChain withDecision(String nextDecisionId, String nextPlanId) {
    return new CorrelationChain(clickId, contextId, nextDecisionId, nextPlanId, executionId);
  }
}
