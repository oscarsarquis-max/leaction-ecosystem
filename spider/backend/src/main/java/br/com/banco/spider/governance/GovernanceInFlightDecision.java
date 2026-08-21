package br.com.banco.spider.governance;

public enum GovernanceInFlightDecision {
  ALLOW_FIXED_SNAPSHOT,
  STOP_BEFORE_EFFECT,
  REQUIRE_MANUAL_REVIEW,
  ALLOW_NON_EFFECTING_STATE_TRANSITION
}
