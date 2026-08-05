package br.com.banco.spider.domain;

import jakarta.validation.constraints.NotBlank;
import java.util.Map;

/**
 * Payload contextual de entrada no orquestrador.
 * Não é o sistema de registro do cliente — apenas o contrato de orquestração.
 */
public record ContextualPayload(
    @NotBlank String productCode,
    String customerExternalId,
    Map<String, Object> context) {}
