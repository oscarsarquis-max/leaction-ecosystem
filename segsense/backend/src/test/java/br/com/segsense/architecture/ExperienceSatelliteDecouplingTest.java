package br.com.segsense.architecture;

import static org.junit.jupiter.api.Assertions.assertFalse;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

class ExperienceSatelliteDecouplingTest {

  @Test
  void segsenseDoesNotDependOnProviderMockRuntime() throws IOException {
    for (Path root : List.of(Path.of("src/main"), Path.of("../frontend/src"))) {
      if (!Files.exists(root)) {
        continue;
      }
      try (Stream<Path> files = Files.walk(root)) {
        files
            .filter(
                path ->
                    path.toString().endsWith(".java")
                        || path.toString().endsWith(".ts")
                        || path.toString().endsWith(".tsx"))
            .forEach(
                path -> {
                  try {
                    String src = Files.readString(path);
                    assertFalse(
                        src.contains("segsense-provider-mock"),
                        () -> path + " must not reference segsense-provider-mock");
                    assertFalse(src.contains(":8095"), () -> path + " must not call mock port");
                    assertFalse(
                        src.contains("illustrative-protection-items"),
                        () -> path + " must not call provider mock path");
                    assertFalse(
                        src.contains("/v1/demo/segsense"),
                        () -> path + " must not call the deprecated demo slice");
                  } catch (IOException e) {
                    throw new RuntimeException(e);
                  }
                });
      }
    }
  }
}
