package br.com.banco.spider.config;

import br.com.banco.spider.application.security.CanonicalExecutionAuthorizationPort;
import br.com.banco.spider.application.security.CanonicalIngressAuthenticationPort;
import br.com.banco.spider.application.security.DenyAllCanonicalExecutionAuthorizationAdapter;
import br.com.banco.spider.application.security.DenyAllCanonicalIngressAuthenticationAdapter;
import br.com.banco.spider.application.security.DenyAllExternalSignalIngressAuthenticationAdapter;
import br.com.banco.spider.application.security.ExternalSignalIngressAuthenticationPort;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class CanonicalSecurityDefaultsConfig {

  @Bean
  @ConditionalOnMissingBean(CanonicalIngressAuthenticationPort.class)
  CanonicalIngressAuthenticationPort denyAllIngressAuthentication() {
    return new DenyAllCanonicalIngressAuthenticationAdapter();
  }

  @Bean
  @ConditionalOnMissingBean(CanonicalExecutionAuthorizationPort.class)
  CanonicalExecutionAuthorizationPort denyAllExecutionAuthorization() {
    return new DenyAllCanonicalExecutionAuthorizationAdapter();
  }

  @Bean
  @ConditionalOnMissingBean(ExternalSignalIngressAuthenticationPort.class)
  ExternalSignalIngressAuthenticationPort denyAllSignalIngressAuthentication() {
    return new DenyAllExternalSignalIngressAuthenticationAdapter();
  }

  @Bean
  @ConditionalOnMissingBean(br.com.banco.spider.execution.callback.CallbackAuthorizationPort.class)
  br.com.banco.spider.execution.callback.CallbackAuthorizationPort denyAllCallbackAuthorization() {
    return new br.com.banco.spider.execution.callback.DenyAllCallbackAuthorizationAdapter();
  }
}
