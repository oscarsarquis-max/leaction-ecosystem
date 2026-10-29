package br.com.banco.spider.application.security;

import java.util.Set;

/**
 * Allowlist do ingress canônico no profile {@code sandbox}. Não reutiliza {@code
 * local-demo-console} e não é produção.
 */
public final class SandboxCanonicalCredentials {

  public static final String CREDENTIAL_REF = "sandbox-operator";
  public static final String ORIGINATOR_ID = "console-sandbox";
  public static final String CHANNEL = "operational-console";
  public static final String PRINCIPAL_REF = "owner:sandbox";
  public static final String CAPABILITY = "mock";
  public static final String SIGNAL_SECURITY_PROFILE_REF = "profile:signal:test@1.0";
  public static final String SIGNAL_SOURCE_REF = "source:mock-async@1.0";
  public static final String DEMO_OPERATION = "SUCCESS_MULTI_STEP";

  /** Os seis cenários da aba Simulação do Monitor. Isolados no adapter mock. */
  public static final Set<String> DEMO_OPERATIONS =
      Set.of(
          "SUCCESS_MULTI_STEP",
          "RETRY_THEN_SUCCESS",
          "BUSINESS_NEGATIVE",
          "WAIT_SIGNAL_RESUME",
          "CALLBACK_RECONCILIATION",
          "TECHNICAL_FAILURE");

  private SandboxCanonicalCredentials() {}

  public static boolean credentialAllowed(String credentialMaterialRef) {
    return CREDENTIAL_REF.equals(credentialMaterialRef);
  }

  public static boolean operationAllowed(String capabilityCode, String operationCode) {
    return CAPABILITY.equals(capabilityCode) && DEMO_OPERATIONS.contains(operationCode);
  }
}
