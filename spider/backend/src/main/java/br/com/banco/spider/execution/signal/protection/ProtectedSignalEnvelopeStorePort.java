package br.com.banco.spider.execution.signal.protection;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

public interface ProtectedSignalEnvelopeStorePort {
  ProtectedSignalEnvelope createOnce(ProtectedSignalEnvelope envelope);

  Optional<ProtectedSignalEnvelope> findByInboxLogicalKey(String inboxLogicalKey);

  Optional<ProtectedSignalEnvelope> claim(
      String inboxLogicalKey, long expectedVersion, String workerId, Instant leaseUntil, Instant now);

  ProtectedSignalEnvelope updateState(
      String inboxLogicalKey,
      long expectedVersion,
      ProtectedEnvelopeState state,
      String leaseOwner,
      Instant leaseUntil,
      Instant consumedAt,
      Instant eligibleForDeletionAt);

  List<ProtectedSignalEnvelope> findByState(ProtectedEnvelopeState state);
}
