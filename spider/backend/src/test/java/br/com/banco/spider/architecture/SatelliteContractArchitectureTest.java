package br.com.banco.spider.architecture;

import static org.junit.jupiter.api.Assertions.assertFalse;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

class SatelliteContractArchitectureTest {

  private static final Path MAIN = Path.of("src/main/java/br/com/banco/spider");

  @Test
  void satelliteCoreDoesNotNameSegSenseIcatuOrMockProduct() throws IOException {
    Path satellite = MAIN.resolve("satellite");
    try (Stream<Path> files = Files.walk(satellite)) {
      files
          .filter(path -> path.toString().endsWith(".java"))
          .forEach(
              path -> {
                try {
                  String src = Files.readString(path);
                  assertFalse(src.contains("SegSense"), () -> path + " must not mention SegSense");
                  assertFalse(src.contains("Icatu"), () -> path + " must not mention Icatu");
                  assertFalse(src.contains("segsense-provider-mock"), () -> path + " must not mention mock product path");
                } catch (IOException e) {
                  throw new RuntimeException(e);
                }
              });
    }
  }

  @Test
  void canonicalEndpointIsNotNamedSegSense() throws IOException {
    Path controller =
        MAIN.resolve("integration/inbound/http/satellite/SatelliteInteractionHttpController.java");
    String src = Files.readString(controller);
    assertFalse(src.contains("/v1/demo/segsense"));
    assertFalse(src.contains("/segsense/"));
  }
}
