package br.com.banco.spider.governance;

import java.util.List;
import java.util.Objects;

/** Descriptor lógico de binding — somente MOCK neste incremento. */
public record BindingDescriptor(
    String bindingCode,
    String version,
    AdapterKind adapterKind,
    List<String> supportedContractRefs,
    List<String> supportedOperationRefs,
    List<String> supportedConfirmationModes,
    List<String> securityProfileRefs,
    List<String> capabilities,
    GovernanceLifecycleState status) {

  public BindingDescriptor {
    Objects.requireNonNull(bindingCode, "bindingCode");
    Objects.requireNonNull(version, "version");
    Objects.requireNonNull(adapterKind, "adapterKind");
    Objects.requireNonNull(status, "status");
    supportedContractRefs = supportedContractRefs == null ? List.of() : List.copyOf(supportedContractRefs);
    supportedOperationRefs =
        supportedOperationRefs == null ? List.of() : List.copyOf(supportedOperationRefs);
    supportedConfirmationModes =
        supportedConfirmationModes == null ? List.of() : List.copyOf(supportedConfirmationModes);
    securityProfileRefs = securityProfileRefs == null ? List.of() : List.copyOf(securityProfileRefs);
    capabilities = capabilities == null ? List.of() : List.copyOf(capabilities);
    if (adapterKind != AdapterKind.MOCK) {
      throw new IllegalArgumentException("Only MOCK bindings eligible in this increment");
    }
    rejectForbidden(bindingCode);
    rejectForbidden(version);
    for (String s : supportedContractRefs) {
      rejectForbidden(s);
    }
  }

  public String exactRef() {
    return bindingCode + "@" + version;
  }

  public boolean isExecutable() {
    return status == GovernanceLifecycleState.PUBLISHED && adapterKind == AdapterKind.MOCK;
  }

  private static void rejectForbidden(String value) {
    if (value == null) {
      return;
    }
    String l = value.toLowerCase();
    if (l.contains("://")
        || l.contains("jdbc:")
        || l.startsWith("http")
        || l.contains("password")
        || l.contains("secret")
        || l.contains("token=")) {
      throw new IllegalArgumentException("forbidden physical/secret content in binding");
    }
  }
}
