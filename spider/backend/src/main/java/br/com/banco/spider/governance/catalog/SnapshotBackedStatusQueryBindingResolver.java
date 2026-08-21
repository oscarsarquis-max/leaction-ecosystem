package br.com.banco.spider.governance.catalog;

import br.com.banco.spider.execution.callback.CallbackDeliveryStatusQueryPort;
import br.com.banco.spider.execution.callback.CallbackStatusQueryBindingResolver;
import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import br.com.banco.spider.governance.AdapterKind;
import br.com.banco.spider.governance.BindingDescriptor;
import java.util.Optional;
import reactor.core.publisher.Mono;

public final class SnapshotBackedStatusQueryBindingResolver
    implements CallbackStatusQueryBindingResolver {

  private final ActiveGovernanceSnapshot snapshot;
  private final CallbackDeliveryStatusQueryPort mockStatusQuery;

  public SnapshotBackedStatusQueryBindingResolver(
      ActiveGovernanceSnapshot snapshot, CallbackDeliveryStatusQueryPort mockStatusQuery) {
    this.snapshot = snapshot;
    this.mockStatusQuery = mockStatusQuery;
  }

  @Override
  public Mono<Optional<CallbackDeliveryStatusQueryPort>> resolve(String statusQueryBindingRef) {
    if (statusQueryBindingRef == null || statusQueryBindingRef.isBlank()) {
      return Mono.just(Optional.empty());
    }
    BindingDescriptor desc = snapshot.bindingDescriptors().get(statusQueryBindingRef.trim());
    if (desc == null || desc.adapterKind() != AdapterKind.MOCK || !desc.isExecutable()) {
      return Mono.just(Optional.empty());
    }
    return Mono.just(Optional.ofNullable(mockStatusQuery));
  }
}
