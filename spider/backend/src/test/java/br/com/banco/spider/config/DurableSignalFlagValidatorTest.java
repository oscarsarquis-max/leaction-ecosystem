package br.com.banco.spider.config;

import static org.assertj.core.api.Assertions.assertThatThrownBy;

import br.com.banco.spider.security.dataprotection.DataProtectionKeyMaterialProviderPort;
import br.com.banco.spider.security.dataprotection.mock.MockDataProtectionKeyMaterialProvider;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;

class DurableSignalFlagValidatorTest {

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
  void durableWithoutTokenFails() {
    var validator =
        new DataProtectionConfig.DurableSignalFlagValidator(
            true, false, true, true, provider(null));
    assertThatThrownBy(validator::validate).isInstanceOf(IllegalStateException.class);
  }

  @Test
  void durableWithoutKeyProviderFails() {
    var validator =
        new DataProtectionConfig.DurableSignalFlagValidator(
            true, true, true, true, provider(null));
    assertThatThrownBy(validator::validate).isInstanceOf(IllegalStateException.class);
  }

  @Test
  void durableWithMockProviderOk() {
    DataProtectionKeyMaterialProviderPort keys = new MockDataProtectionKeyMaterialProvider();
    var validator =
        new DataProtectionConfig.DurableSignalFlagValidator(
            true, true, true, true, provider(keys));
    validator.validate();
  }
}
