package br.com.banco.spider.security.replay;

import java.time.Instant;

public interface ReplayGuardPort {

  ReplayDecision reserve(ReplayReservation candidate);

  int cleanupExpired(Instant now, int batchSize);
}
