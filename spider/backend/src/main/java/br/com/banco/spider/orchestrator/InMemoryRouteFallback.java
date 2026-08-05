package br.com.banco.spider.orchestrator;

import br.com.banco.spider.model.ProductRoute;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Fallback em memória quando a rota não está no PostgreSQL. */
@Component
public class InMemoryRouteFallback {

  private final Map<String, ProductRoute> routes = new ConcurrentHashMap<>();

  public InMemoryRouteFallback(
      @Value("${spider.legado.base-url}") String legadoBaseUrl,
      @Value("${spider.legado.process-path}") String processPath) {
    String endpoint = legadoBaseUrl + processPath;
    routes.put(
        "CONTA_DIGITAL_ONBOARDING",
        ProductRoute.builder()
            .productCode("CONTA_DIGITAL_ONBOARDING")
            .name("Onboarding Conta Digital (fallback)")
            .enabled(true)
            .version(1)
            .definitionJson(
                "{\"legacyEndpoint\":\""
                    + endpoint
                    + "\",\"steps\":[{\"name\":\"processar_legado\",\"system\":\"legado-financeiro\"}]}")
            .build());
    routes.put(
        "DEFAULT",
        ProductRoute.builder()
            .productCode("DEFAULT")
            .name("Rota padrão legado financeiro")
            .enabled(true)
            .version(1)
            .definitionJson("{\"legacyEndpoint\":\"" + endpoint + "\"}")
            .build());
  }

  public Optional<ProductRoute> find(String productId) {
    ProductRoute route = routes.get(productId);
    if (route != null) {
      return Optional.of(route);
    }
    return Optional.ofNullable(routes.get("DEFAULT"));
  }
}
