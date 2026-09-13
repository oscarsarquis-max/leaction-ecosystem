package br.com.segsense.application.satellite;

import java.util.List;

public record SatelliteManifest(
    String classification,
    String schemaVersion,
    String schemaVersionKind,
    String applicationId,
    String domain,
    List<String> allowedOperationClasses,
    String mutationPolicy,
    String status,
    boolean executable,
    boolean acceptedBySpider) {}
