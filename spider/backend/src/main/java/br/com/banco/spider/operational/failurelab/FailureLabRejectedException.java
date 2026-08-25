package br.com.banco.spider.operational.failurelab;

/** Recusa segura de um pedido ao Failure Lab. Só carrega código estável de motivo. */
public class FailureLabRejectedException extends RuntimeException {

  public static final String DISABLED = "FAILURE_LAB_DISABLED";
  public static final String SCENARIO_NOT_FOUND = "SCENARIO_NOT_FOUND";
  public static final String PARAMETER_NOT_ALLOWED = "PARAMETER_NOT_ALLOWED";
  public static final String CONCURRENCY_LIMIT_REACHED = "CONCURRENCY_LIMIT_REACHED";

  private final String reasonCode;

  public FailureLabRejectedException(String reasonCode) {
    super(reasonCode);
    this.reasonCode = FailureLabRedaction.safeReason(reasonCode);
  }

  public String reasonCode() {
    return reasonCode;
  }
}
