package br.com.segsense.inbound.http.link;

public record RevokeContextLinkRequest(Long expectedVersion, String justification) {}
