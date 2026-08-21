package br.com.banco.spider.architecture;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

class PersistenceArchitectureTest {

  @Test
  void persistencePortsDoNotImportJpa() throws Exception {
    Path dir = Path.of("src/main/java/br/com/banco/spider/execution/persistence");
    try (var walk = Files.walk(dir)) {
      walk.filter(p -> p.toString().endsWith(".java"))
          .forEach(
              p -> {
                try {
                  String src = Files.readString(p);
                  assertFalse(src.contains("jakarta.persistence"), p.toString());
                  assertFalse(src.contains("JpaRepository"), p.toString());
                } catch (Exception e) {
                  throw new RuntimeException(e);
                }
              });
    }
  }

  @Test
  void engineDoesNotCallRepositoriesDirectly() throws Exception {
    String src =
        Files.readString(
            Path.of(
                "src/main/java/br/com/banco/spider/execution/engine/DefaultCanonicalExecutionEngine.java"));
    assertFalse(src.contains("JpaRepository"));
    assertFalse(src.contains("infrastructure.persistence.jpa"));
    assertTrue(src.contains("ReactiveExecutionPersistenceGateway"));
    assertFalse(src.contains(".block("));
  }

  @Test
  void blockingSupportUsesSubscribeOn() throws Exception {
    String src =
        Files.readString(
            Path.of(
                "src/main/java/br/com/banco/spider/infrastructure/persistence/BlockingPersistenceSupport.java"));
    assertTrue(src.contains("subscribeOn"));
  }
}
