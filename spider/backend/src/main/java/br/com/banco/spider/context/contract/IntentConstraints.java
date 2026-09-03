package br.com.banco.spider.context.contract;

/** Restrições explícitas que atravessam a fronteira probabilística/determinística. */
public record IntentConstraints(
    Boolean mutationAllowed, Boolean readOnly, Boolean confirmationRequired) {

  public static IntentConstraints readOnlyWithConfirmation() {
    return new IntentConstraints(false, true, true);
  }
}
