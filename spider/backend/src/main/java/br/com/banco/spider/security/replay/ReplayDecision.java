package br.com.banco.spider.security.replay;

import java.util.Objects;

public record ReplayDecision(ReplayDecisionStatus status, ReplayReservation reservation) {
  public ReplayDecision {
    Objects.requireNonNull(status, "status");
  }
}
