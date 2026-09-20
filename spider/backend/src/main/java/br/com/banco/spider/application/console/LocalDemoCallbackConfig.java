package br.com.banco.spider.application.console;

import br.com.banco.spider.application.security.LocalDemoCanonicalCredentials;
import br.com.banco.spider.execution.callback.CallbackAuthorizationPort;
import br.com.banco.spider.execution.callback.CallbackBindingResolverPort;
import br.com.banco.spider.execution.callback.CallbackDefinition;
import br.com.banco.spider.execution.callback.CallbackDefinitionCatalogPort;
import br.com.banco.spider.execution.callback.CallbackDeliveryPolicy;
import br.com.banco.spider.execution.callback.CallbackDeliveryPolicyCatalogPort;
import br.com.banco.spider.execution.callback.CallbackProjectionKind;
import br.com.banco.spider.execution.callback.ConfiguredCallbackBindingResolver;
import br.com.banco.spider.execution.callback.ConfiguredCallbackDefinitionCatalog;
import br.com.banco.spider.execution.callback.ConfiguredCallbackDeliveryPolicyCatalog;
import br.com.banco.spider.execution.callback.OriginatorMatchedCallbackAuthorizationAdapter;
import br.com.banco.spider.execution.callback.delivery.MockCallbackAdapter;
import java.util.List;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;

/**
 * Catálogo Mock de callback para o cenário canônico da Simulação. Não é Reconciliation Workbench
 * (CAP-021): só publica a definição e o adapter já existentes para o outbox entregar.
 */
@Configuration
@Profile("local-demo")
@ConditionalOnProperty(name = "spider.console.local-demo.enabled", havingValue = "true")
public class LocalDemoCallbackConfig {

  @Bean
  @Primary
  CallbackDefinitionCatalogPort localDemoCallbackDefinitionCatalog() {
    return new ConfiguredCallbackDefinitionCatalog(
        List.of(
            CallbackDefinition.published(
                DemoCanonicalRouteSupport.CALLBACK_REF,
                DemoCanonicalRouteSupport.CALLBACK_VERSION,
                DemoCanonicalRouteSupport.CALLBACK_BINDING,
                "contract:callback:result@1.0",
                "profile:callback:local-demo@1.0",
                DemoCanonicalRouteSupport.CALLBACK_POLICY,
                CallbackProjectionKind.MINIMAL_STATUS_V1.name(),
                List.of(LocalDemoCanonicalCredentials.ORIGINATOR_ID),
                "INTERNAL")));
  }

  @Bean
  @Primary
  CallbackDeliveryPolicyCatalogPort localDemoCallbackDeliveryPolicyCatalog() {
    return new ConfiguredCallbackDeliveryPolicyCatalog(
        List.of(
            CallbackDeliveryPolicy.publishedDefault(
                "policy:cb-local-demo", "1.0")));
  }

  @Bean
  @Primary
  CallbackAuthorizationPort localDemoCallbackAuthorization() {
    return new OriginatorMatchedCallbackAuthorizationAdapter();
  }

  @Bean
  @Primary
  CallbackBindingResolverPort localDemoCallbackBindingResolver() {
    return new ConfiguredCallbackBindingResolver(
        Map.of(
            DemoCanonicalRouteSupport.CALLBACK_BINDING,
            new MockCallbackAdapter(MockCallbackAdapter.Scenario.DELIVERED)));
  }
}
