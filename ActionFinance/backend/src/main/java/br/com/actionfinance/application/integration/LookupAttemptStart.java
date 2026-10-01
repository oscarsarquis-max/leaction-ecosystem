package br.com.actionfinance.application.integration;

import java.time.Instant;
import java.util.UUID;

public record LookupAttemptStart(
        UUID attemptId, String attemptCorrelationId, ExternalLookupView operation, Instant startedAt) {}
