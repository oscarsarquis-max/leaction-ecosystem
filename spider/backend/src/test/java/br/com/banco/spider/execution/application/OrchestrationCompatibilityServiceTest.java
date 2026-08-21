package br.com.banco.spider.execution.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import br.com.banco.spider.canonical.validation.CanonicalStructuralValidator;
import br.com.banco.spider.domain.OrchestrationOutcome;
import br.com.banco.spider.domain.ProductOrchestrateRequest;
import br.com.banco.spider.integration.mapping.ProductOrchestrateCanonicalMapper;
import br.com.banco.spider.orchestrator.OrchestrationService;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Map;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

class OrchestrationCompatibilityServiceTest {

  @Test
  void delegatesToLegacyBaselineWithoutDuplicatingCall() {
    ObjectMapper mapper = new ObjectMapper();
    ProductOrchestrateCanonicalMapper canonicalMapper =
        new ProductOrchestrateCanonicalMapper(mapper);
    CanonicalStructuralValidator validator = new CanonicalStructuralValidator();
    OrchestrationService legacy = mock(OrchestrationService.class);

    OrchestrationOutcome outcome =
        new OrchestrationOutcome(
            "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
            "CONTA_DIGITAL_ONBOARDING",
            "tx-1",
            "OK",
            200,
            12L,
            "jwt-token",
            Map.of("ok", true));

    when(legacy.orchestrate(any(), anyString())).thenReturn(Mono.just(outcome));

    OrchestrationCompatibilityService service =
        new OrchestrationCompatibilityService(canonicalMapper, validator, legacy);

    ProductOrchestrateRequest request =
        new ProductOrchestrateRequest("CONTA_DIGITAL_ONBOARDING", "tx-1", Map.of("canal", "test"));

    StepVerifier.create(
            service.orchestrate(
                request, "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"))
        .assertNext(
            result -> {
              assertEquals(200, result.legacyHttpStatus());
              assertNotNull(result.stateTransitionToken());
            })
        .verifyComplete();

    verify(legacy).orchestrate(any(), anyString());
  }
}
