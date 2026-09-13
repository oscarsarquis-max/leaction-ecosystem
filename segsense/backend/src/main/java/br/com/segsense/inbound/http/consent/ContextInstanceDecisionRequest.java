package br.com.segsense.inbound.http.consent;

public record ContextInstanceDecisionRequest(
    Long expectedVersion, Integer noticeVersion, Boolean acknowledged) {}
