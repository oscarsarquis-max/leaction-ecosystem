package br.com.banco.spider.security.replay;

public enum ReplayDecisionStatus {
  RESERVED,
  DUPLICATE_SAME_MESSAGE,
  REPLAY_CONFLICT,
  EXPIRED_PROOF,
  CAPACITY_REJECTED
}
