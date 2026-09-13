package br.com.segsense.domain.consent;

import java.time.Instant;
import java.util.UUID;

public record NoticeAdministrativeDecision(
    UUID id,
    UUID noticeId,
    int noticeVersion,
    String contentHash,
    String decisionType,
    String justification,
    String actor,
    Instant occurredAt) {}
