package br.com.banco.spider.integration.mock;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.canonical.contract.CanonicalPayload;
import br.com.banco.spider.canonical.contract.TraceDescriptor;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.integration.port.AdapterDispositionMode;
import br.com.banco.spider.integration.port.UniversalAdapterPort;
import br.com.banco.spider.integration.port.UniversalAdapterRequest;
import br.com.banco.spider.integration.port.UniversalAdapterResult;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import reactor.test.StepVerifier;

class MockUniversalAdapterTest {

  private final ObjectMapper mapper = new ObjectMapper();
  private final UniversalAdapterPort port = new MockUniversalAdapter(mapper);

  @Test
  void engineDependsOnlyOnPortInterface() {
    assertTrue(port instanceof UniversalAdapterPort);
  }

  @Test
  void successScenario() {
    StepVerifier.create(port.invoke(request(MockAdapterScenario.SUCCESS)))
        .assertNext(
            result -> {
              assertEquals(AdapterDispositionMode.COMPLETED, result.dispositionMode());
              assertEquals(TechnicalStatus.SUCCESS, result.outcome().technicalStatus());
              assertEquals("corr-stable", result.correlationId());
              assertTrue(result.errors().isEmpty());
            })
        .verifyComplete();
  }

  @Test
  void technicalFailureNormalized() {
    StepVerifier.create(port.invoke(request(MockAdapterScenario.TECHNICAL_FAILURE)))
        .assertNext(
            result -> {
              assertEquals(AdapterDispositionMode.REJECTED, result.dispositionMode());
              assertTrue(result.errors().stream().anyMatch(e -> e.code().startsWith("UNAV_")));
              assertEquals("corr-stable", result.correlationId());
            })
        .verifyComplete();
  }

  @Test
  void timeoutProducesCanonicalError() {
    StepVerifier.create(port.invoke(request(MockAdapterScenario.TIMEOUT)))
        .assertNext(
            result -> {
              assertEquals(AdapterDispositionMode.REJECTED, result.dispositionMode());
              assertTrue(result.errors().stream().anyMatch(e -> e.code().startsWith("TIME_")));
            })
        .verifyComplete();
  }

  @Test
  void unknownDisposition() {
    StepVerifier.create(port.invoke(request(MockAdapterScenario.UNKNOWN)))
        .assertNext(
            result -> assertEquals(AdapterDispositionMode.UNKNOWN, result.dispositionMode()))
        .verifyComplete();
  }

  @Test
  void businessNegativeKeepsTechnicalSuccess() {
    StepVerifier.create(port.invoke(request(MockAdapterScenario.BUSINESS_NEGATIVE)))
        .assertNext(
            result -> {
              assertEquals(AdapterDispositionMode.COMPLETED, result.dispositionMode());
              assertEquals(TechnicalStatus.SUCCESS, result.outcome().technicalStatus());
              assertTrue(result.outcome().businessOutcome() != null);
            })
        .verifyComplete();
  }

  private UniversalAdapterRequest request(MockAdapterScenario scenario) {
    ObjectNode data = mapper.createObjectNode();
    data.put("mockScenario", scenario.name());
    return UniversalAdapterRequest.builder()
        .invocationId("inv-1")
        .executionId("exec-1")
        .stepId("step-1")
        .attemptId("attempt-1")
        .invokedAt(Instant.now())
        .capabilityCode("CAP")
        .operationCode("OP")
        .bindingRef("binding:mock@1.0.0")
        .trace(
            new TraceDescriptor(
                "corr-stable",
                "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
                null))
        .payload(CanonicalPayload.of(data))
        .build();
  }
}
