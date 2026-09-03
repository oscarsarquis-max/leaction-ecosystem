package br.com.banco.spider.application.security;

import java.util.Set;

/**
 * Allowlist do ingress canônico em {@code local-demo}. Não é permitAll: credencial, originador e
 * canal precisam coincidir com o mecanismo previsto do console Mock.
 */
public final class LocalDemoCanonicalCredentials {

  public static final String CREDENTIAL_REF = "local-demo-console";
  public static final String ORIGINATOR_ID = "console-local-demo";
  public static final String CHANNEL = "operational-console";
  public static final String PRINCIPAL_REF = "owner:local-demo";
  public static final String CAPABILITY = "mock";

  public static final Set<String> DEMO_OPERATIONS =
      Set.of(
          "SUCCESS_MULTI_STEP",
          "RETRY_THEN_SUCCESS",
          "BUSINESS_NEGATIVE",
          "WAIT_SIGNAL_RESUME",
          "WAIT_AND_RESUME",
          "CALLBACK_RECONCILIATION",
          "CALLBACK_UNCERTAIN",
          "TECHNICAL_FAILURE",
          "TECHNICAL_TERMINAL_FAILURE",
          "SIGNAL_SECURITY_REJECTED",
          "OPERATIONAL_DEGRADATION");

  private LocalDemoCanonicalCredentials() {}

  public static boolean credentialAllowed(String credentialMaterialRef) {
    return CREDENTIAL_REF.equals(credentialMaterialRef);
  }

  public static boolean operationAllowed(String capabilityCode, String operationCode) {
    return CAPABILITY.equals(capabilityCode) && DEMO_OPERATIONS.contains(operationCode);
  }
}
