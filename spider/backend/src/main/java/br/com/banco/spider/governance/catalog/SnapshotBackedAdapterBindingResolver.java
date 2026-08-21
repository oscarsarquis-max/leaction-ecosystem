package br.com.banco.spider.governance.catalog;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import br.com.banco.spider.governance.AdapterKind;
import br.com.banco.spider.governance.BindingDescriptor;
import br.com.banco.spider.integration.binding.AdapterBindingResolution;
import br.com.banco.spider.integration.binding.AdapterBindingResolverPort;
import br.com.banco.spider.integration.port.UniversalAdapterPort;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import reactor.core.publisher.Mono;

/**
 * Resolve refs de binding do snapshot para o Adapter Mock conhecido — sem reflection/class loading.
 */
public final class SnapshotBackedAdapterBindingResolver implements AdapterBindingResolverPort {

  private final ActiveGovernanceSnapshot snapshot;
  private final UniversalAdapterPort mockAdapter;

  public SnapshotBackedAdapterBindingResolver(
      ActiveGovernanceSnapshot snapshot, UniversalAdapterPort mockAdapter) {
    this.snapshot = snapshot;
    this.mockAdapter = mockAdapter;
  }

  @Override
  public Mono<AdapterBindingResolution> resolve(String adapterBindingRef) {
    return Mono.fromCallable(
        () -> {
          if (adapterBindingRef == null || adapterBindingRef.isBlank()) {
            return AdapterBindingResolution.missing(
                List.of(error("BINDING_REF_REQUIRED", "adapterBindingRef is required")));
          }
          BindingDescriptor desc = snapshot.bindingDescriptors().get(adapterBindingRef.trim());
          if (desc == null) {
            return AdapterBindingResolution.missing(
                List.of(
                    error(
                        "BINDING_NOT_FOUND",
                        "No binding in snapshot for ref=" + adapterBindingRef)));
          }
          if (desc.adapterKind() != AdapterKind.MOCK || !desc.isExecutable()) {
            return AdapterBindingResolution.missing(
                List.of(error("BINDING_NOT_EXECUTABLE", "Only MOCK published bindings eligible")));
          }
          return AdapterBindingResolution.ok(mockAdapter);
        });
  }

  private static CanonicalError error(String code, String message) {
    return CanonicalError.builder()
        .errorId("err-" + UUID.randomUUID())
        .code(code)
        .category(ErrorCategory.RESOLUTION)
        .severity(ErrorSeverity.ERROR)
        .message(message)
        .retryable(false)
        .occurredAt(Instant.now())
        .source(new CanonicalError.ErrorSource("snapshot_adapter_binding_resolver", null, null, null))
        .build();
  }
}
