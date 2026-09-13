package br.com.segsense.inbound.http.opportunity;

public record GovernanceCommandRequest(
    Long expectedVersion, Integer revisionNumber, String justification) {}
