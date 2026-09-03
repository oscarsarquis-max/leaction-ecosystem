package br.com.banco.spider.context.application.port;

/** Falha provider-neutral ao desserializar ou validar a saída estruturada. */
public final class InvalidContextInterpretationResponseException extends RuntimeException {

  public InvalidContextInterpretationResponseException(String message) {
    super(message);
  }

  public InvalidContextInterpretationResponseException(String message, Throwable cause) {
    super(message, cause);
  }
}
