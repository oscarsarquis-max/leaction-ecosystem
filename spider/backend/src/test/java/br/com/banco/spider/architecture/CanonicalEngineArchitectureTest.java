package br.com.banco.spider.architecture;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.integration.mock.MockUniversalAdapter;
import br.com.banco.spider.integration.port.UniversalAdapterPort;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

/**
 * Guardas estruturais do PROMPT-002 — sem ArchUnit (evita dependência nova).
 */
class CanonicalEngineArchitectureTest {

  private static final Path MAIN =
      Path.of("src/main/java/br/com/banco/spider");

  @Test
  void executionEngineDoesNotDependOnIntegrationMock() throws IOException {
    Path engineDir = MAIN.resolve("execution");
    try (Stream<Path> files = Files.walk(engineDir)) {
      files
          .filter(p -> p.toString().endsWith(".java"))
          .forEach(
              path -> {
                try {
                  String src = Files.readString(path);
                  assertFalse(
                      src.contains("integration.mock"),
                      () -> path + " must not import integration.mock");
                  assertFalse(
                      src.contains("MockUniversalAdapter"),
                      () -> path + " must not reference MockUniversalAdapter");
                } catch (IOException e) {
                  throw new RuntimeException(e);
                }
              });
    }
  }

  @Test
  void routeAndPlanModelsDoNotDependOnWebClientHttpOrJpa() throws IOException {
    for (String pkg : new String[] {"execution/route", "execution/plan", "execution/runtime"}) {
      Path dir = MAIN.resolve(pkg);
      try (Stream<Path> files = Files.walk(dir)) {
        files
            .filter(p -> p.toString().endsWith(".java"))
            .forEach(
                path -> {
                  try {
                    String src = Files.readString(path);
                    assertFalse(src.contains("org.springframework.web"));
                    assertFalse(src.contains("WebClient"));
                    assertFalse(src.contains("jakarta.persistence"));
                    assertFalse(src.contains("javax.persistence"));
                    assertFalse(src.contains("org.springframework.data"));
                  } catch (IOException e) {
                    throw new RuntimeException(e);
                  }
                });
      }
    }
  }

  @Test
  void mockAdapterImplementsUniversalPort() {
    assertTrue(UniversalAdapterPort.class.isAssignableFrom(MockUniversalAdapter.class));
  }

  @Test
  void centralEngineDoesNotImportControllerOrLegacyDto() throws IOException {
    Path engine =
        MAIN.resolve("execution/engine/DefaultCanonicalExecutionEngine.java");
    String src = Files.readString(engine);
    assertFalse(src.contains("web.controller"));
    assertFalse(src.contains("ProductOrchestrateRequest"));
    assertFalse(src.contains("OrchestrationService"));
  }
}
