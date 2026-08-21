package br.com.banco.spider.governance;

/** Erros tipados do loader histórico. */
public final class GovernanceContextException extends IllegalStateException {

  private final String reasonCode;

  public GovernanceContextException(String reasonCode, String message) {
    super(message == null ? reasonCode : message);
    this.reasonCode = reasonCode;
  }

  public String reasonCode() {
    return reasonCode;
  }

  public static GovernanceContextException of(String reasonCode) {
    return new GovernanceContextException(reasonCode, reasonCode);
  }
}
