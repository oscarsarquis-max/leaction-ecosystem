package br.com.banco.spider.canonical.error;

/**
 * Categorias canônicas de erro (SPIDER-ARCH-004). Serialização por nome estável.
 */
public enum ErrorCategory {
  VALIDATION,
  AUTHENTICATION,
  AUTHORIZATION,
  RESOLUTION,
  CONTRACT,
  IDEMPOTENCY,
  TIMEOUT,
  UNAVAILABLE,
  RATE_LIMITED,
  BUSINESS_OUTCOME,
  INTERNAL
}
