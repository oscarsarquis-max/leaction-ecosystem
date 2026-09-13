package br.com.segsense.infrastructure.consent;

import br.com.segsense.application.consent.ContextInstanceTtlSettings;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class ContextInstanceConfiguration {

  @Bean
  ContextInstanceTtlSettings contextInstanceTtlSettings(
      @Value("${segsense.context-instance.ttl:PT24H}") Duration ttl) {
    return new ContextInstanceTtlSettings(ttl);
  }
}
