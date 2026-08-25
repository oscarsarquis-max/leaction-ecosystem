package br.com.banco.spider.implementation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

class ImplementationManifestLoaderTest {

  private final ObjectMapper mapper = new ObjectMapper().findAndRegisterModules();
  private final ImplementationManifestLoader loader = new ImplementationManifestLoader(mapper);

  @Test
  void loadsValidManifestWithCorrectStatuses() {
    var m = loader.loadAndValidate();
    assertEquals("SPIDER-PROMPT-018", m.currentPrompt());
    assertEquals("GROUP_A_VISIBILITY_OBSERVABILITY", m.currentGroup());
    assertEquals(26, m.capabilities().size());
    assertEquals(240, m.baseline().backendTests());
    assertEquals(25, m.baseline().frontendTests());
    assertEquals(0, m.baseline().skipped());
    for (var c : m.capabilities()) {
      int n = Integer.parseInt(c.promptRef().substring("SPIDER-PROMPT-".length()));
      if (n <= 18) {
        assertEquals("VERIFIED", c.status(), c.capabilityCode());
        assertEquals("MOCK_ONLY", c.integrationLevel(), c.capabilityCode());
      } else {
        assertEquals("PLANNED", c.status(), c.capabilityCode());
      }
    }
  }

  @Test
  void architectureAndTechnicalRefsExistOnDisk() throws Exception {
    var m = loader.loadAndValidate();
    Path root = Path.of("..").toAbsolutePath().normalize();
    if (!Files.isDirectory(root.resolve("docs"))) {
      root = Path.of(".").toAbsolutePath().normalize();
    }
    // tests run from backend/
    Path repo = Path.of(".").toAbsolutePath().normalize().getParent();
    for (var c : m.capabilities()) {
      for (String ref : c.architectureRefs()) {
        assertTrue(Files.exists(repo.resolve(ref)), () -> "missing " + ref);
      }
      for (String ref : c.technicalDocRefs()) {
        assertTrue(Files.exists(repo.resolve(ref)), () -> "missing " + ref);
      }
    }
  }

  @Test
  void mockPhaseNeverProduction() {
    var m = loader.loadAndValidate();
    assertTrue(
        m.capabilities().stream().noneMatch(c -> "PRODUCTION".equals(c.integrationLevel())));
  }
}
