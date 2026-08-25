package br.com.banco.spider.operational.workers;

/**
 * Conjunto fechado de tipos de worker. Cada tipo tem um processador canônico já existente — o
 * runtime apenas dá durabilidade ao agendamento, nunca inventa trabalho novo.
 */
public enum WorkerType {
  SIGNAL_APPLICATION,
  WAIT_EXPIRY,
  CALLBACK_DELIVERY,
  CALLBACK_RECONCILIATION,
  CALLBACK_RECOVERY,
  SIGNAL_APPLICATION_RECOVERY,
  PROTECTED_ENVELOPE_MAINTENANCE;

  public boolean recovery() {
    return this == CALLBACK_RECOVERY || this == SIGNAL_APPLICATION_RECOVERY;
  }
}
