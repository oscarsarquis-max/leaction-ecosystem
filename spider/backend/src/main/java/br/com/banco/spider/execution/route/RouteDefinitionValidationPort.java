package br.com.banco.spider.execution.route;

import br.com.banco.spider.canonical.error.CanonicalError;
import java.util.List;

public interface RouteDefinitionValidationPort {
  List<CanonicalError> validate(RouteDefinition route);

  default boolean isValid(RouteDefinition route) {
    return validate(route).isEmpty();
  }
}
