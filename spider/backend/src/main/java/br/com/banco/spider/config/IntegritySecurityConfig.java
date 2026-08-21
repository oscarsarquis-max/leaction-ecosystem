package br.com.banco.spider.config;

import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryReplayGuardAdapter;
import br.com.banco.spider.security.integrity.ConfiguredIntegrityProfileCatalog;
import br.com.banco.spider.security.integrity.CryptographicKeyMaterialProviderPort;
import br.com.banco.spider.security.integrity.IntegrityKeyRotationService;
import br.com.banco.spider.security.integrity.IntegrityProfileCatalogPort;
import br.com.banco.spider.security.integrity.MessageIntegrityService;
import br.com.banco.spider.security.integrity.mock.MockCryptographicKeyMaterialProvider;
import br.com.banco.spider.security.replay.ReplayGuardCleanupService;
import br.com.banco.spider.security.replay.ReplayGuardPort;
import java.util.List;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class IntegritySecurityConfig {

  @Bean
  @ConditionalOnMissingBean(IntegrityProfileCatalogPort.class)
  IntegrityProfileCatalogPort emptyIntegrityProfileCatalog() {
    return new ConfiguredIntegrityProfileCatalog(List.of());
  }

  @Bean
  @ConditionalOnMissingBean(IntegrityKeyRotationService.class)
  IntegrityKeyRotationService integrityKeyRotationService() {
    return new IntegrityKeyRotationService();
  }

  @Bean
  @ConditionalOnProperty(name = "spider.security.mock-key-provider.enabled", havingValue = "true")
  CryptographicKeyMaterialProviderPort mockCryptographicKeyMaterialProvider() {
    return new MockCryptographicKeyMaterialProvider();
  }

  @Bean
  @ConditionalOnProperty(name = "spider.security.integrity.enabled", havingValue = "true")
  @org.springframework.boot.autoconfigure.condition.ConditionalOnBean(
      CryptographicKeyMaterialProviderPort.class)
  MessageIntegrityService messageIntegrityService(
      CryptographicKeyMaterialProviderPort keyProvider,
      IntegrityProfileCatalogPort profileCatalog,
      IntegrityKeyRotationService rotationService,
      SpiderClock clock) {
    return new MessageIntegrityService(keyProvider, profileCatalog, rotationService, clock);
  }

  @Bean
  @ConditionalOnProperty(
      name = "spider.canonical.persistence.mode",
      havingValue = "memory",
      matchIfMissing = true)
  @ConditionalOnMissingBean(ReplayGuardPort.class)
  ReplayGuardPort inMemoryReplayGuardPort() {
    return new InMemoryReplayGuardAdapter();
  }

  @Bean
  @ConditionalOnMissingBean(ReplayGuardCleanupService.class)
  ReplayGuardCleanupService replayGuardCleanupService(ReplayGuardPort replayGuard) {
    return new ReplayGuardCleanupService(replayGuard);
  }
}
