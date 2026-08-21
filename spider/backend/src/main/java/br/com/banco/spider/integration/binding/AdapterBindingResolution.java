package br.com.banco.spider.integration.binding;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.integration.port.UniversalAdapterPort;
import java.util.List;
import java.util.Optional;

public record AdapterBindingResolution(
    boolean resolved, UniversalAdapterPort adapter, List<CanonicalError> errors) {

  public AdapterBindingResolution {
    errors = errors == null ? List.of() : List.copyOf(errors);
  }

  public static AdapterBindingResolution ok(UniversalAdapterPort adapter) {
    return new AdapterBindingResolution(true, adapter, List.of());
  }

  public static AdapterBindingResolution missing(List<CanonicalError> errors) {
    return new AdapterBindingResolution(false, null, errors);
  }

  public Optional<UniversalAdapterPort> adapterOptional() {
    return Optional.ofNullable(adapter);
  }
}
