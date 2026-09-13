package br.com.segsense.domain.demonstration;

import java.time.Instant;
import java.util.UUID;

public record DemonstrationDecision(
    UUID id,
    int revisionNumber,
    String action,
    String actor,
    String justification,
    Instant decidedAt) {}
