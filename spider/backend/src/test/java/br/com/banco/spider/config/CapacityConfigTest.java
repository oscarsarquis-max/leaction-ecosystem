package br.com.banco.spider.config;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;

import br.com.banco.spider.operational.capacity.CapacityDecisionStore;
import java.util.function.Consumer;
import org.junit.jupiter.api.Test;

/** O governo de capacidade é desligado por omissão e nenhuma superfície dele existe sozinha. */
class CapacityConfigTest {

  @Test
  void defaultsAreDisabledAndValid() {
    CapacityProperties properties = new CapacityProperties();

    assertDoesNotThrow(() -> CapacityConfig.validate(properties));
    assertFalse(properties.isEnabled());
    assertFalse(properties.getHttp().isEnabled());
    assertFalse(properties.getLocalDemo().isEnabled());
    assertFalse(properties.getEnforcement().isEnabled());
    assertEquals(CapacityDecisionStore.MAX_SIZE, properties.getDecisionLogSize());
  }

  @Test
  void httpSurfaceRequiresTheModuleItself() {
    assertRejected(properties -> properties.getHttp().setEnabled(true));
  }

  @Test
  void localDemoRequiresTheModuleItself() {
    assertRejected(properties -> properties.getLocalDemo().setEnabled(true));
  }

  @Test
  void enforcementRequiresTheModuleItself() {
    assertRejected(properties -> properties.getEnforcement().setEnabled(true));
  }

  @Test
  void decisionLogSizeStaysInsideTheDeclaredBounds() {
    assertRejected(properties -> properties.setDecisionLogSize(0));
    assertRejected(properties -> properties.setDecisionLogSize(CapacityDecisionStore.MAX_SIZE + 1));
  }

  @Test
  void everySurfaceIsAcceptedOnceTheModuleIsOn() {
    CapacityProperties properties = new CapacityProperties();
    properties.setEnabled(true);
    properties.getHttp().setEnabled(true);
    properties.getLocalDemo().setEnabled(true);
    properties.getEnforcement().setEnabled(true);

    assertDoesNotThrow(() -> CapacityConfig.validate(properties));
  }

  private static void assertRejected(Consumer<CapacityProperties> mutation) {
    CapacityProperties properties = new CapacityProperties();
    mutation.accept(properties);
    assertThrows(IllegalStateException.class, () -> CapacityConfig.validate(properties));
  }
}
