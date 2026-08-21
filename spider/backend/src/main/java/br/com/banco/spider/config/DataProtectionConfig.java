package br.com.banco.spider.config;

import br.com.banco.spider.security.dataprotection.DataProtectionKeyMaterialProviderPort;
import br.com.banco.spider.security.dataprotection.mock.MockDataProtectionKeyMaterialProvider;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class DataProtectionConfig {

  private static final Logger log = LoggerFactory.getLogger(DataProtectionConfig.class);

  @Bean
  @ConditionalOnProperty(
      name = "spider.signal.envelope-protection.mock-key-provider.enabled",
      havingValue = "true")
  DataProtectionKeyMaterialProviderPort mockDataProtectionKeyMaterialProvider() {
    return new MockDataProtectionKeyMaterialProvider();
  }

  /** Valida combinação de flags quando durable-application=true. */
  public static class DurableSignalFlagValidator {
    private final boolean durable;
    private final boolean tokenEnabled;
    private final boolean requireToken;
    private final boolean envelopeProtection;
    private final ObjectProvider<DataProtectionKeyMaterialProviderPort> keyProvider;

    DurableSignalFlagValidator(
        boolean durable,
        boolean tokenEnabled,
        boolean requireToken,
        boolean envelopeProtection,
        ObjectProvider<DataProtectionKeyMaterialProviderPort> keyProvider) {
      this.durable = durable;
      this.tokenEnabled = tokenEnabled;
      this.requireToken = requireToken;
      this.envelopeProtection = envelopeProtection;
      this.keyProvider = keyProvider;
    }

    public void validate() {
      if (!durable) {
        return;
      }
      if (requireToken && !tokenEnabled) {
        throw new IllegalStateException(
            "durable-application requires spider.signal.continuation-token.enabled=true");
      }
      if (!envelopeProtection) {
        throw new IllegalStateException(
            "durable-application requires spider.signal.envelope-protection.enabled=true");
      }
      if (keyProvider.getIfAvailable() == null) {
        throw new IllegalStateException(
            "durable-application requires DataProtectionKeyMaterialProviderPort (enable mock-key-provider)");
      }
      log.info("event=durable_signal_flags_validated reasonCode=OK");
    }
  }

  @Bean
  DurableSignalFlagValidator durableSignalFlagValidator(
      @Value("${spider.signal.ingress.durable-application.enabled:false}") boolean durable,
      @Value("${spider.signal.continuation-token.enabled:false}") boolean tokenEnabled,
      @Value("${spider.signal.continuation-token.require-for-durable:true}") boolean requireToken,
      @Value("${spider.signal.envelope-protection.enabled:false}") boolean envelopeProtection,
      ObjectProvider<DataProtectionKeyMaterialProviderPort> keyProvider) {
    DurableSignalFlagValidator v =
        new DurableSignalFlagValidator(
            durable, tokenEnabled, requireToken, envelopeProtection, keyProvider);
    v.validate();
    return v;
  }
}
