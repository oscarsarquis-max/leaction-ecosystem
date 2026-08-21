package br.com.banco.spider.execution.persistence.port;

import br.com.banco.spider.execution.inbox.InboxProcessingState;
import br.com.banco.spider.execution.inbox.InboxRecord;
import br.com.banco.spider.execution.inbox.InboxReservationResult;
import br.com.banco.spider.execution.inbox.InboxValidationState;
import java.util.List;
import java.util.Optional;

public interface InboxStorePort {
  InboxReservationResult reserve(InboxRecord candidate);

  Optional<InboxRecord> find(String sourceRef, String messageId);

  InboxRecord updateStates(
      String sourceRef,
      String messageId,
      InboxValidationState validationState,
      InboxProcessingState processingState,
      String payloadRef,
      String errorCode);

  List<InboxRecord> findByProcessingState(InboxProcessingState state);

  List<InboxRecord> findInterruptedProcessing();

  List<InboxRecord> findDueForApplication(java.time.Instant now, int limit);

  java.util.Optional<InboxRecord> claimForApplication(
      String sourceRef,
      String messageId,
      long expectedVersion,
      String workerId,
      java.time.Instant leaseUntil,
      java.time.Instant now);

  InboxRecord updateApplicationState(
      String sourceRef,
      String messageId,
      long expectedVersion,
      InboxProcessingState processingState,
      String leaseOwner,
      java.time.Instant leaseUntil,
      java.time.Instant nextAttemptAt,
      int applicationAttemptCount,
      String errorCode,
      java.time.Instant appliedAt,
      java.time.Instant now);
}
