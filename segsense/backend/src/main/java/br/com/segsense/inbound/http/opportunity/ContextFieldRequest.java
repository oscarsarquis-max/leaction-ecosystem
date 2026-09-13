package br.com.segsense.inbound.http.opportunity;

import java.util.List;

public record ContextFieldRequest(
    String key,
    String label,
    String type,
    Boolean required,
    String source,
    String classification,
    List<String> allowedValues) {}
