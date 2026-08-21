package br.com.banco.spider.architecture;

import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

class OrchestrateEndpointRegressionTest {

  @Test
  void controllerStillDelegatesToCompatibilityLegacyBaseline() throws Exception {
    Path controller =
        Path.of(
            "src/main/java/br/com/banco/spider/web/controller/ProductOrchestratorController.java");
    String src = Files.readString(controller);
    assertTrue(src.contains("OrchestrationCompatibilityService"));
    assertTrue(src.contains("/orchestrate"));
    assertTrue(src.contains("orchestrationCompatibilityService.orchestrate"));
    assertTrue(!src.contains("CanonicalExecutionEngine"));
  }

  @Test
  void compatibilityServiceStillDelegatesToOrchestrationService() throws Exception {
    Path service =
        Path.of(
            "src/main/java/br/com/banco/spider/execution/application/OrchestrationCompatibilityService.java");
    String src = Files.readString(service);
    assertTrue(src.contains("orchestrationService.orchestrate"));
    assertTrue(!src.contains("CanonicalExecutionEngine"));
  }
}
