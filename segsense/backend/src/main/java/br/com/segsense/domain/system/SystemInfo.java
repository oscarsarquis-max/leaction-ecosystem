package br.com.segsense.domain.system;

public record SystemInfo(
    String name, String version, String applicationId, OperationalState operationalState) {}
