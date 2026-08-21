package br.com.banco.spider.governance.catalog;

import br.com.banco.spider.execution.callback.CallbackBindingResolverPort;
import br.com.banco.spider.execution.callback.CallbackDeliveryPort;
import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import br.com.banco.spider.governance.AdapterKind;
import br.com.banco.spider.governance.BindingDescriptor;
import java.util.Optional;
import reactor.core.publisher.Mono;

public final class SnapshotBackedCallbackBindingResolver implements CallbackBindingResolverPort {

  private final ActiveGovernanceSnapshot snapshot;
  private final CallbackDeliveryPort mockDelivery;

  public SnapshotBackedCallbackBindingResolver(
      ActiveGovernanceSnapshot snapshot, CallbackDeliveryPort mockDelivery) {
    this.snapshot = snapshot;
    this.mockDelivery = mockDelivery;
  }

  @Override
  public Mono<Optional<CallbackDeliveryPort>> resolve(String bindingRef) {
    if (bindingRef == null || bindingRef.isBlank()) {
      return Mono.just(Optional.empty());
    }
    BindingDescriptor desc = snapshot.bindingDescriptors().get(bindingRef.trim());
    if (desc == null || desc.adapterKind() != AdapterKind.MOCK || !desc.isExecutable()) {
      return Mono.just(Optional.empty());
    }
    return Mono.just(Optional.ofNullable(mockDelivery));
  }
}
