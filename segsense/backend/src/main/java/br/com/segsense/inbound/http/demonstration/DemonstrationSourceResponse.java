package br.com.segsense.inbound.http.demonstration;

import java.util.UUID;

public record DemonstrationSourceResponse(
    UUID id,
    String key,
    String url,
    String consultedOn,
    String accessKind,
    String verificationStatus,
    String summary) {}
