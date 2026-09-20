package br.com.banco.spider.integration.outbound.provider;

import br.com.banco.spider.satellite.application.SatelliteRegistry;
import br.com.banco.spider.satellite.application.SatelliteRegistry.ProviderBinding;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import reactor.core.publisher.Mono;

public final class DispatchingProviderCapabilityAdapter implements ProviderCapabilityPort {

  private final HttpProviderCapabilityAdapter insurance;
  private final HttpCreditProviderCapabilityAdapter credit;
  private final SatelliteRegistry registry;

  public DispatchingProviderCapabilityAdapter(
      HttpProviderCapabilityAdapter insurance,
      HttpCreditProviderCapabilityAdapter credit,
      SatelliteRegistry registry) {
    this.insurance = insurance;
    this.credit = credit;
    this.registry = registry;
  }

  @Override
  public Mono<ExecutionResult> execute(ExecutionRequest request) {
    ProviderBinding binding = registry.resolveProviderBinding(request.capabilityId());
    if (binding != null && HttpCreditProviderCapabilityAdapter.PROVIDER_ID.equals(binding.providerId())) {
      return credit.execute(request);
    }
    return insurance.execute(request);
  }
}
