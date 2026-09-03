package br.com.banco.spider.integration.inbound.http.canonical;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.integration.inbound.http.canonical.dto.CanonicalExecutionHttpRequest;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import java.time.Instant;
import org.junit.jupiter.api.Test;

class CanonicalExecutionHttpMapperTest {

  private final CanonicalExecutionHttpMapper mapper =
      new CanonicalExecutionHttpMapper(new ObjectMapper().registerModule(new JavaTimeModule()));

  @Test
  void assignsExecutionIdWhenClientOmitsIt() {
    CanonicalExecutionHttpRequest http =
        new CanonicalExecutionHttpRequest(
            new CanonicalExecutionHttpRequest.ContractDto("1.0", "1.0.0"),
            new CanonicalExecutionHttpRequest.ExecutionDto(null, Instant.parse("2026-09-03T12:00:00Z"), "idem-1"),
            new CanonicalExecutionHttpRequest.ContextDto("c", "i", "cap", "p", "j"),
            new CanonicalExecutionHttpRequest.OriginDto("operational-console", "console-local-demo", "ix"),
            new CanonicalExecutionHttpRequest.TraceDto(
                "corr-1", "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01", null),
            new CanonicalExecutionHttpRequest.TargetDto("mock", "RETRY_THEN_SUCCESS"),
            new CanonicalExecutionHttpRequest.PayloadDto(null),
            null);
    var canonical = mapper.toCanonical(http);
    assertNotNull(canonical.execution().executionId());
    assertTrue(canonical.execution().executionId().startsWith("exec-"));
  }
}
