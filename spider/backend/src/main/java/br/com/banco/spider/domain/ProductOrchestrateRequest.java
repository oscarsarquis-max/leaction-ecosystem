package br.com.banco.spider.domain;

import jakarta.validation.constraints.NotBlank;
import java.util.Map;

/** Intenção de produto enviada pelo service-originador. */
public record ProductOrchestrateRequest(
    @NotBlank String productId,
    @NotBlank String transactionId,
    Map<String, Object> payload) {}
