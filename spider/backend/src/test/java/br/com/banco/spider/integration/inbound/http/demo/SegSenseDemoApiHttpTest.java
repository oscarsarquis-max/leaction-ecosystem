package br.com.banco.spider.integration.inbound.http.demo;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import br.com.banco.spider.demo.segsense.SegSenseDemoApplicationAuth;
import br.com.banco.spider.demo.segsense.SegSenseDemoOriginSnapshot;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ResultItem;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.reactive.server.WebTestClient;
import reactor.core.publisher.Mono;

@SpringBootTest(
    properties = {
      "spider.context.ai.enabled=false",
      "spider.demo.segsense.enabled=true",
      "spider.demo.segsense.application-secret=segsense-http-test-only",
      "spider.demo.segsense.mock-credential=segsense-mock-http-test-only",
      "spider.satellite.enabled=true",
      "spider.satellite.registry.segsense.secret=segsense-http-test-only",
      "spider.satellite.providers.insurance-provider-mock.secret=segsense-mock-http-test-only"
    })
@AutoConfigureWebTestClient(timeout = "PT30S")
@ActiveProfiles("local-demo")
class SegSenseDemoApiHttpTest {

  private static final String TEST_SECRET = "segsense-http-test-only";

  @Autowired WebTestClient client;
  @MockBean ProviderCapabilityPort provider;

  @Test
  void rejectsMissingApplicationCredential() {
    client
        .post()
        .uri("/v1/demo/segsense/protection-decisions")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(Map.of())
        .exchange()
        .expectStatus()
        .isUnauthorized();
  }

  @Test
  void consoleIdentityDoesNotOpenThisRoute() {
    client
        .post()
        .uri("/v1/demo/segsense/protection-decisions")
        .header("X-Spider-Credential-Ref", "local-demo-console")
        .header(SegSenseDemoApplicationAuth.SECRET_HEADER, TEST_SECRET)
        .header("X-Correlation-ID", "11111111-1111-1111-1111-111111111111")
        .header("Idempotency-Key", "k-console")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(happyBody())
        .exchange()
        .expectStatus()
        .isUnauthorized();
  }

  @Test
  void missingOriginIsRejectedBeforeMock() {
    client
        .post()
        .uri("/v1/demo/segsense/protection-decisions")
        .header("X-Spider-Credential-Ref", "local-demo-segsense")
        .header(SegSenseDemoApplicationAuth.SECRET_HEADER, TEST_SECRET)
        .header("X-Correlation-ID", "11111111-1111-1111-1111-111111111111")
        .header("Idempotency-Key", "k-no-origin")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(
            Map.of(
                "contractVersion", "segsense-demo-contract-v1",
                "applicationId", "SEGSENSE",
                "scenarioKey", "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1",
                "declaredObjective", "UNDERSTAND_FAMILY_PROTECTION_OPTIONS"))
        .exchange()
        .expectStatus()
        .isBadRequest();
    verify(provider, never()).execute(any());
  }

  @Test
  void happyPathDelegatesToCanonicalDecision() {
    when(provider.execute(any()))
        .thenReturn(
            Mono.just(
                new ExecutionResult(
                    true,
                    "COMPLETED",
                    "preq-9",
                    "insurance-provider-mock",
                    "ill-9",
                    "ILLUSTRATIVE_NOT_ICATU_CONTRACT",
                    "DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO",
                    List.of(new ResultItem("STEP", "Revisar", "JOURNEY_STEP", true)),
                    List.of("Pendência"))));
    client
        .post()
        .uri("/v1/demo/segsense/protection-decisions")
        .header("X-Spider-Credential-Ref", "local-demo-segsense")
        .header(SegSenseDemoApplicationAuth.SECRET_HEADER, TEST_SECRET)
        .header("X-Correlation-ID", "11111111-1111-1111-1111-111111111111")
        .header("Idempotency-Key", "k-ok-demo")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(happyBody())
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.status")
        .isEqualTo("PRE_PROPOSAL_READY")
        .jsonPath("$.demoEndpointDeprecated")
        .isEqualTo(true)
        .jsonPath("$.decisionProvenance")
        .isEqualTo("SPIDER_SATELLITE_CONTRACT_V1")
        .jsonPath("$.planId")
        .doesNotExist();
  }

  private static Map<String, Object> happyBody() {
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("contractVersion", "segsense-demo-contract-v1");
    body.put("applicationId", "SEGSENSE");
    body.put("scenarioKey", "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1");
    body.put("originSnapshot", SegSenseDemoOriginSnapshot.governed().toMap());
    body.put("declaredObjective", "UNDERSTAND_FAMILY_PROTECTION_OPTIONS");
    return body;
  }
}
