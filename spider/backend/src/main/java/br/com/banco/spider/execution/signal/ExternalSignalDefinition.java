package br.com.banco.spider.execution.signal;

import br.com.banco.spider.governance.GovernanceLifecycleState;
import java.time.Duration;
import java.util.List;
import java.util.Objects;

/** Artifact governado — sem endpoint, secret ou key material. */
public record ExternalSignalDefinition(
    String signalCode,
    String version,
    String contractRef,
    List<String> allowedEventTypes,
    String integrityProfileRef,
    String authenticationProfileRef,
    String authorizationPolicyRef,
    String inputMappingRef,
    int maximumPayloadBytes,
    int maximumMetadataEntries,
    Duration acceptedClockSkew,
    Duration replayWindow,
    LateSignalPolicy lateSignalPolicy,
    UnknownFieldPolicy unknownFieldPolicy,
    GovernanceLifecycleState status,
    String definitionIntegrityRef,
    String dataProtectionProfileRef) {

  public ExternalSignalDefinition {
    signalCode = Objects.requireNonNull(signalCode, "signalCode").trim();
    version = Objects.requireNonNull(version, "version").trim();
    contractRef = Objects.requireNonNull(contractRef, "contractRef").trim();
    allowedEventTypes =
        allowedEventTypes == null ? List.of() : List.copyOf(allowedEventTypes);
    integrityProfileRef = Objects.requireNonNull(integrityProfileRef, "integrityProfileRef").trim();
    authenticationProfileRef =
        blankToNull(authenticationProfileRef) == null
            ? "authn:signal:deny-all@1.0"
            : authenticationProfileRef.trim();
    authorizationPolicyRef =
        blankToNull(authorizationPolicyRef) == null
            ? "authz:signal:deny-all@1.0"
            : authorizationPolicyRef.trim();
    inputMappingRef =
        blankToNull(inputMappingRef) == null ? "STATUS_ONLY_V1" : inputMappingRef.trim();
    Objects.requireNonNull(acceptedClockSkew, "acceptedClockSkew");
    Objects.requireNonNull(replayWindow, "replayWindow");
    Objects.requireNonNull(lateSignalPolicy, "lateSignalPolicy");
    Objects.requireNonNull(unknownFieldPolicy, "unknownFieldPolicy");
    Objects.requireNonNull(status, "status");
    if (maximumPayloadBytes <= 0 || maximumPayloadBytes > 262_144) {
      throw new IllegalArgumentException("maximumPayloadBytes out of range");
    }
    if (maximumMetadataEntries < 0 || maximumMetadataEntries > 64) {
      throw new IllegalArgumentException("maximumMetadataEntries out of range");
    }
    if (acceptedClockSkew.isNegative() || acceptedClockSkew.compareTo(Duration.ofMinutes(15)) > 0) {
      throw new IllegalArgumentException("acceptedClockSkew out of range");
    }
    if (replayWindow.isNegative() || replayWindow.isZero() || replayWindow.compareTo(Duration.ofDays(7)) > 0) {
      throw new IllegalArgumentException("replayWindow out of range");
    }
    definitionIntegrityRef = blankToNull(definitionIntegrityRef);
    dataProtectionProfileRef = blankToNull(dataProtectionProfileRef);
  }

  /** Compat sem DP ref. */
  public ExternalSignalDefinition(
      String signalCode,
      String version,
      String contractRef,
      List<String> allowedEventTypes,
      String integrityProfileRef,
      String authenticationProfileRef,
      String authorizationPolicyRef,
      String inputMappingRef,
      int maximumPayloadBytes,
      int maximumMetadataEntries,
      Duration acceptedClockSkew,
      Duration replayWindow,
      LateSignalPolicy lateSignalPolicy,
      UnknownFieldPolicy unknownFieldPolicy,
      GovernanceLifecycleState status,
      String definitionIntegrityRef) {
    this(
        signalCode,
        version,
        contractRef,
        allowedEventTypes,
        integrityProfileRef,
        authenticationProfileRef,
        authorizationPolicyRef,
        inputMappingRef,
        maximumPayloadBytes,
        maximumMetadataEntries,
        acceptedClockSkew,
        replayWindow,
        lateSignalPolicy,
        unknownFieldPolicy,
        status,
        definitionIntegrityRef,
        null);
  }

  public String ref() {
    return "signal:" + signalCode + "@" + version;
  }

  public boolean isEligible() {
    return status == GovernanceLifecycleState.PUBLISHED;
  }

  public static ExternalSignalDefinition publishedMock(
      String code, String version, String contractRef, String integrityProfileRef) {
    return publishedMock(code, version, contractRef, integrityProfileRef, null);
  }

  public static ExternalSignalDefinition publishedMock(
      String code,
      String version,
      String contractRef,
      String integrityProfileRef,
      String dataProtectionProfileRef) {
    return new ExternalSignalDefinition(
        code,
        version,
        contractRef,
        List.of("ASYNC_COMPLETION", "STATUS_UPDATE"),
        integrityProfileRef,
        "authn:signal:deny-all@1.0",
        "authz:signal:deny-all@1.0",
        "STATUS_ONLY_V1",
        65_536,
        16,
        Duration.ofMinutes(5),
        Duration.ofHours(24),
        LateSignalPolicy.RECORD_ONLY,
        UnknownFieldPolicy.REJECT,
        GovernanceLifecycleState.PUBLISHED,
        null,
        dataProtectionProfileRef);
  }

  private static String blankToNull(String v) {
    if (v == null || v.isBlank()) {
      return null;
    }
    return v.trim();
  }
}
