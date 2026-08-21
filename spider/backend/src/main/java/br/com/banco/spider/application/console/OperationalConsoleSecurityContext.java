package br.com.banco.spider.application.console;

public record OperationalConsoleSecurityContext(
    String principalRef, String assuranceLevel, boolean authenticated) {
  public static OperationalConsoleSecurityContext anonymous() {
    return new OperationalConsoleSecurityContext("anonymous", "NONE", false);
  }
}
