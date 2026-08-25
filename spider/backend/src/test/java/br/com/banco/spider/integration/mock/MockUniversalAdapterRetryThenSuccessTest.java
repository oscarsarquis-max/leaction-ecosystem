package br.com.banco.spider.integration.mock;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.canonical.contract.CanonicalPayload;
import br.com.banco.spider.canonical.contract.TraceDescriptor;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.integration.port.AdapterDispositionMode;
import br.com.banco.spider.integration.port.UniversalAdapterPort;
import br.com.banco.spider.integration.port.UniversalAdapterRequest;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import reactor.test.StepVerifier;

class MockUniversalAdapterRetryThenSuccessTest {

  private final ObjectMapper mapper = new ObjectMapper();
  private final UniversalAdapterPort port = new MockUniversalAdapter(mapper);

  @Test
  void firstInvocationFailsWithARetryableErrorAndSecondSucceeds() {
    StepVerifier.create(port.invoke(request("exec-retry-1", "step-1", "attempt-1")))
        .assertNext(
            result -> {
              assertEquals(AdapterDispositionMode.REJECTED, result.dispositionMode());
              assertEquals(TechnicalStatus.FAILURE, result.outcome().technicalStatus());
              assertTrue(
                  result.errors().stream()
                      .anyMatch(error -> error.code().equals("UNAV_MOCK_TRANSIENT")));
              assertTrue(result.errors().stream().allMatch(error -> Boolean.TRUE.equals(error.retryable())));
            })
        .verifyComplete();

    StepVerifier.create(port.invoke(request("exec-retry-1", "step-1", "attempt-2")))
        .assertNext(
            result -> {
              assertEquals(AdapterDispositionMode.COMPLETED, result.dispositionMode());
              assertEquals(TechnicalStatus.SUCCESS, result.outcome().technicalStatus());
              assertTrue(result.errors().isEmpty());
            })
        .verifyComplete();
  }

  @Test
  void transientFailureIsScopedToTheExecutionAndStepPair() {
    StepVerifier.create(port.invoke(request("exec-retry-2", "step-1", "attempt-1")))
        .assertNext(result -> assertEquals(AdapterDispositionMode.REJECTED, result.dispositionMode()))
        .verifyComplete();

    StepVerifier.create(port.invoke(request("exec-retry-3", "step-1", "attempt-1")))
        .assertNext(result -> assertEquals(AdapterDispositionMode.REJECTED, result.dispositionMode()))
        .verifyComplete();

    StepVerifier.create(port.invoke(request("exec-retry-2", "step-1", "attempt-2")))
        .assertNext(result -> assertEquals(AdapterDispositionMode.COMPLETED, result.dispositionMode()))
        .verifyComplete();
  }

  private UniversalAdapterRequest request(String executionId, String stepId, String attemptId) {
    ObjectNode data = mapper.createObjectNode();
    data.put("mockScenario", MockAdapterScenario.RETRY_THEN_SUCCESS.name());
    return UniversalAdapterRequest.builder()
        .invocationId("inv-" + attemptId)
        .executionId(executionId)
        .stepId(stepId)
        .attemptId(attemptId)
        .invokedAt(Instant.now())
        .capabilityCode("mock")
        .operationCode("RETRY_THEN_SUCCESS")
        .bindingRef("binding:mock@1.0.0")
        .trace(
            new TraceDescriptor(
                "corr-" + executionId,
                "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
                null))
        .payload(CanonicalPayload.of(data))
        .build();
  }
}
