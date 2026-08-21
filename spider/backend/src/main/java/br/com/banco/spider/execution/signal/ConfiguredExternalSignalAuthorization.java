package br.com.banco.spider.execution.signal;

import java.util.Set;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

/** Deny-by-default: apenas principals/sources cadastrados (fixture de teste). */
@Component
public class ConfiguredExternalSignalAuthorization implements ExternalSignalAuthorizationPort {

  private final Set<String> allowedPrincipals;
  private final Set<String> allowedSources;

  @org.springframework.beans.factory.annotation.Autowired
  public ConfiguredExternalSignalAuthorization() {
    this(
        Set.of("principal:test-signal@1.0"),
        Set.of("source:mock-async@1.0", "source:test-signal@1.0"));
  }

  public ConfiguredExternalSignalAuthorization(Set<String> principals, Set<String> sources) {
    this.allowedPrincipals = Set.copyOf(principals);
    this.allowedSources = Set.copyOf(sources);
  }

  @Override
  public Mono<Boolean> authorize(
      SignalSecurityContext context, String bindingRef, String securityProfileRef) {
    if (context == null || bindingRef == null || bindingRef.isBlank()) {
      return Mono.just(false);
    }
    boolean ok =
        allowedPrincipals.contains(context.principalRef())
            && allowedSources.contains(context.sourceRef())
            && (securityProfileRef == null
                || securityProfileRef.isBlank()
                || securityProfileRef.equals(context.securityProfileRef()));
    return Mono.just(ok);
  }
}
