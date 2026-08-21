package br.com.banco.spider.execution.fingerprint;

/** Hash estável da chave — nunca persiste a chave em claro. */
public interface IdempotencyKeyHashPort {
  String hash(String idempotencyKey);
}
