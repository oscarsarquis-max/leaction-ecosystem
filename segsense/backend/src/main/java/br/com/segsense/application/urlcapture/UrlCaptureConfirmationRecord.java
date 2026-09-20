package br.com.segsense.application.urlcapture;

import java.time.Instant;
import java.util.UUID;

public record UrlCaptureConfirmationRecord(
    UUID id,
    UUID captureId,
    Instant confirmedAt,
    String confirmedElementsJson,
    String correctionsJson,
    String correlationId) {}
