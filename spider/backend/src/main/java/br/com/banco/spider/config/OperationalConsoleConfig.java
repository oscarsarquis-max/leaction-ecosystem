package br.com.banco.spider.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;

@Configuration
@EnableConfigurationProperties(OperationalConsoleProperties.class)
public class OperationalConsoleConfig {

  public OperationalConsoleConfig(
      OperationalConsoleProperties props, Environment environment) {
    if (props.getHttp().isEnabled() && !props.isEnabled()) {
      throw new IllegalStateException(
          "spider.console.http.enabled=true requer spider.console.enabled=true");
    }
    if (props.getLocalDemo().isEnabled()) {
      boolean localDemoProfile = false;
      for (String p : environment.getActiveProfiles()) {
        if ("local-demo".equals(p)) {
          localDemoProfile = true;
          break;
        }
      }
      if (!localDemoProfile) {
        throw new IllegalStateException(
            "spider.console.local-demo.enabled=true requer profile Spring local-demo");
      }
      if (!props.isEnabled()) {
        throw new IllegalStateException(
            "spider.console.local-demo.enabled=true requer spider.console.enabled=true");
      }
    }
    if (props.getMaxPageSize() < 1 || props.getMaxPageSize() > 100) {
      throw new IllegalStateException("spider.console.max-page-size inválido");
    }
    if (props.getDefaultPageSize() < 1 || props.getDefaultPageSize() > props.getMaxPageSize()) {
      throw new IllegalStateException("spider.console.default-page-size inválido");
    }
  }
}
