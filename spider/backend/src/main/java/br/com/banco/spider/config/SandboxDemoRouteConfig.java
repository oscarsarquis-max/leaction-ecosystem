package br.com.banco.spider.config;

import br.com.banco.spider.application.console.DemoCanonicalRouteSupport;
import br.com.banco.spider.application.security.SandboxCanonicalCredentials;
import br.com.banco.spider.execution.retry.ConfiguredRetryPolicyCatalog;
import br.com.banco.spider.execution.retry.RetryPolicyCatalogPort;
import br.com.banco.spider.execution.route.InMemoryRouteCatalog;
import br.com.banco.spider.execution.route.RouteCatalogPort;
import br.com.banco.spider.execution.route.RouteDefinition;
import br.com.banco.spider.operational.failurelab.FailureLabRouteSupport;
import java.util.List;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;

/**
 * Uma única rota demonstrável no sandbox, isolada de providers reais e sem ativar Failure Lab ou
 * {@code local-demo}.
 */
@Configuration
@Profile("sandbox")
public class SandboxDemoRouteConfig {

  @Bean
  @Primary
  RouteCatalogPort sandboxDemoRouteCatalog() {
    List<RouteDefinition> routes =
        DemoCanonicalRouteSupport.routes().stream()
            .filter(
                route ->
                    SandboxCanonicalCredentials.DEMO_OPERATION.equals(
                        route.target().operationCode()))
            .toList();
    return new InMemoryRouteCatalog(routes);
  }

  @Bean
  @Primary
  RetryPolicyCatalogPort sandboxRetryPolicyCatalog() {
    return new ConfiguredRetryPolicyCatalog(FailureLabRouteSupport.retryPolicies());
  }
}
