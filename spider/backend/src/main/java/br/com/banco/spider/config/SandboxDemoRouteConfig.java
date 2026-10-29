package br.com.banco.spider.config;

import br.com.banco.spider.application.console.DemoCanonicalRouteSupport;
import br.com.banco.spider.application.security.SandboxCanonicalCredentials;
import br.com.banco.spider.execution.retry.ConfiguredRetryPolicyCatalog;
import br.com.banco.spider.execution.retry.RetryPolicyCatalogPort;
import br.com.banco.spider.execution.route.InMemoryRouteCatalog;
import br.com.banco.spider.execution.route.RouteCatalogPort;
import br.com.banco.spider.execution.route.RouteDefinition;
import br.com.banco.spider.operational.failurelab.FailureLabRouteSupport;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;

/**
 * Rotas da aba Simulação no sandbox, isoladas no adapter mock. Inclui o retry já publicado no
 * catálogo do Failure Lab sem abrir o laboratório inteiro nem {@code local-demo}.
 */
@Configuration
@Profile("sandbox")
public class SandboxDemoRouteConfig {

  @Bean
  @Primary
  RouteCatalogPort sandboxDemoRouteCatalog() {
    java.util.ArrayList<RouteDefinition> routes =
        new java.util.ArrayList<>(DemoCanonicalRouteSupport.routes());
    FailureLabRouteSupport.routes().stream()
        .filter(
            route ->
                SandboxCanonicalCredentials.DEMO_OPERATIONS.contains(
                    route.target().operationCode()))
        .forEach(routes::add);
    return new InMemoryRouteCatalog(routes);
  }

  @Bean
  @Primary
  RetryPolicyCatalogPort sandboxRetryPolicyCatalog() {
    return new ConfiguredRetryPolicyCatalog(FailureLabRouteSupport.retryPolicies());
  }

  @Bean
  @Primary
  br.com.banco.spider.execution.wait.WaitPolicyCatalogPort sandboxWaitPolicyCatalog() {
    return new br.com.banco.spider.execution.wait.ConfiguredWaitPolicyCatalog(
        FailureLabRouteSupport.waitPolicies());
  }
}
