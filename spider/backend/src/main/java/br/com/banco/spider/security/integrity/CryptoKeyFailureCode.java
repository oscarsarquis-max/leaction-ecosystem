package br.com.banco.spider.security.integrity;

/** Falhas normalizadas do key provider — sem detalhes internos. */
public enum CryptoKeyFailureCode {
  KEY_NOT_FOUND,
  KEY_VERSION_NOT_ALLOWED,
  KEY_REVOKED,
  KEY_UNAVAILABLE,
  ALGORITHM_MISMATCH,
  PURPOSE_MISMATCH
}
