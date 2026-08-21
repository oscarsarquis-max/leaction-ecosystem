package br.com.banco.spider.security.integrity;

/** Exceção segura — mensagem sem key material. */
public class CryptographicKeyException extends RuntimeException {

  private final CryptoKeyFailureCode code;

  public CryptographicKeyException(CryptoKeyFailureCode code) {
    super(code.name());
    this.code = code;
  }

  public CryptoKeyFailureCode code() {
    return code;
  }

  @Override
  public String toString() {
    return "CryptographicKeyException{code=" + code + "}";
  }
}
