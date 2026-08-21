package br.com.banco.spider.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import br.com.banco.spider.security.dataprotection.DataProtectionKeyMaterialProviderPort;
import br.com.banco.spider.security.dataprotection.mock.MockDataProtectionKeyMaterialProvider;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;

/** Matriz de flags — defaults seguros e fail-closed. */
class DurableFlagMatrixTest {

  private static <T> ObjectProvider<T> provider(T value) {
    return new ObjectProvider<>() {
      @Override
      public T getObject() {
        return value;
      }

      @Override
      public T getObject(Object... args) {
        return value;
      }

      @Override
      public T getIfAvailable() {
        return value;
      }

      @Override
      public T getIfUnique() {
        return value;
      }
    };
  }

  @Test
  void staticBaselineFlagsOk() {
    new DataProtectionConfig.DurableSignalFlagValidator(false, false, true, false, provider(null))
        .validate();
  }

  @Test
  void durableWithoutTokenRejected() {
    assertThatThrownBy(
            () ->
                new DataProtectionConfig.DurableSignalFlagValidator(
                        true, false, true, true, provider(new MockDataProtectionKeyMaterialProvider()))
                    .validate())
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("continuation-token");
  }

  @Test
  void durableWithoutProtectionRejected() {
    assertThatThrownBy(
            () ->
                new DataProtectionConfig.DurableSignalFlagValidator(
                        true, true, true, false, provider(new MockDataProtectionKeyMaterialProvider()))
                    .validate())
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("envelope-protection");
  }

  @Test
  void durableWithoutProviderRejected() {
    assertThatThrownBy(
            () ->
                new DataProtectionConfig.DurableSignalFlagValidator(
                        true, true, true, true, provider(null))
                    .validate())
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("DataProtectionKeyMaterialProviderPort");
  }

  @Test
  void durableFullyConfiguredOk() {
    DataProtectionKeyMaterialProviderPort keys = new MockDataProtectionKeyMaterialProvider();
    new DataProtectionConfig.DurableSignalFlagValidator(true, true, true, true, provider(keys))
        .validate();
    assertThat(keys).isNotNull();
  }
}
