package br.com.banco.spider.integration.binding;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.integration.port.UniversalAdapterPort;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

/**
 * Resolve bindings publicados na configuração. A Engine não conhece o Adapter concreto.
 */
@Component
public class ConfiguredAdapterBindingResolver implements AdapterBindingResolverPort {

  public static final String DEFAULT_MOCK_BINDING = "binding:mock-universal@1.0";

  private final Map<String, UniversalAdapterPort> published;

  @org.springframework.beans.factory.annotation.Autowired
  public ConfiguredAdapterBindingResolver(
      UniversalAdapterPort adapter,
      @Value("${spider.adapter.bindings.mock-ref:" + DEFAULT_MOCK_BINDING + "}") String mockBindingRef) {
    Map<String, UniversalAdapterPort> map = new LinkedHashMap<>();
    map.put(mockBindingRef, adapter);
    this.published = Map.copyOf(map);
  }

  /** Construtor de teste com mapa explícito. */
  public ConfiguredAdapterBindingResolver(Map<String, UniversalAdapterPort> published) {
    this.published = Map.copyOf(published);
  }

  @Override
  public Mono<AdapterBindingResolution> resolve(String adapterBindingRef) {
    return Mono.fromCallable(
        () -> {
          if (adapterBindingRef == null || adapterBindingRef.isBlank()) {
            return AdapterBindingResolution.missing(
                List.of(error("BINDING_REF_REQUIRED", "adapterBindingRef is required")));
          }
          UniversalAdapterPort port = published.get(adapterBindingRef.trim());
          if (port == null) {
            return AdapterBindingResolution.missing(
                List.of(
                    error(
                        "BINDING_NOT_FOUND",
                        "No published adapter binding for ref=" + adapterBindingRef)));
          }
          return AdapterBindingResolution.ok(port);
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
        .source(new CanonicalError.ErrorSource("adapter_binding_resolver", null, null, null))
        .build();
  }
}
