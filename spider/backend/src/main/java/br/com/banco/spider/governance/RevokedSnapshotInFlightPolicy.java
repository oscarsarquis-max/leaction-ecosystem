package br.com.banco.spider.governance;

public enum RevokedSnapshotInFlightPolicy {
  ALLOW_ALREADY_MATERIALIZED,
  STOP_BEFORE_NEXT_EXTERNAL_EFFECT,
  REQUIRE_MANUAL_DECISION
}
