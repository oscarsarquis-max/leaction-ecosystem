package br.com.banco.spider.application.security;

public record ExecutionAuthorizationRequest(
    AuthenticatedOriginator authenticatedOriginator,
    String capabilityCode,
    String operationCode,
    String channel,
    String contractVersion,
    String purposeRef) {}
