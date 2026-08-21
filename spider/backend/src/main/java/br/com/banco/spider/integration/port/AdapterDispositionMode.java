package br.com.banco.spider.integration.port;

/** Disposição imediata da invocação do Adapter (SPIDER-ARCH-006). */
public enum AdapterDispositionMode {
  COMPLETED,
  ACCEPTED_ASYNC,
  REJECTED,
  UNKNOWN
}
