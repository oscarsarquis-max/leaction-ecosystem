package br.com.segsense.inbound.http.opportunity;

import java.util.List;

public record ContextFieldResponse(
    String key,
    String label,
    String type,
    boolean required,
    String source,
    String classification,
    int position,
    List<String> allowedValues) {}
