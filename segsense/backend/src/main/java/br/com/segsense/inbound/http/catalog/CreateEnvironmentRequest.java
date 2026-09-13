package br.com.segsense.inbound.http.catalog;

public record CreateEnvironmentRequest(String key, String name, String type, String canonicalUrl) {}
