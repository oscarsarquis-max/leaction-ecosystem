package br.com.segsense.application.urlcapture;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record UrlCaptureRecord(
    UUID id,
    String requestedUrl,
    String finalUrl,
    String finalHost,
    Instant capturedAt,
    Integer httpStatus,
    String contentType,
    String title,
    String detectedLanguage,
    String excerpt,
    String normalizedText,
    String bytesSha256,
    String textSha256,
    String extractorVersion,
    String resultCode,
    String extractedElementsJson,
    String correlationId,
    Instant createdAt) {}
