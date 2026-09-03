package br.com.banco.spider.integration.inbound.http.context;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.application.security.LocalDemoCanonicalCredentials;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.reactive.server.WebTestClient;

@SpringBootTest
@AutoConfigureWebTestClient(timeout = "PT30S")
@ActiveProfiles("local-demo")
class ContextIntelligenceHttpTest {

  @Autowired WebTestClient client;
  @Autowired ObjectMapper mapper;

  @Test
  void contextCatalogIsDeterministicAndDoesNotClaimAi() {
    client
        .get()
        .uri("/v1/context/intents")
        .header("X-Spider-Credential-Ref", LocalDemoCanonicalCredentials.CREDENTIAL_REF)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.contextEnabled")
        .isEqualTo(true)
        .jsonPath("$.uiEnabled")
        .isEqualTo(true)
        .jsonPath("$.aiEnabled")
        .isEqualTo(false)
        .jsonPath("$.items.length()")
        .isEqualTo(6)
        .jsonPath("$.items[0].intentContract.provenance.source")
        .isEqualTo("BUSINESS_CARD");
  }

  @Test
  void contextEndpointsPreserveDenyAllWithoutCredential() {
    client.get().uri("/v1/context/intents").exchange().expectStatus().isUnauthorized();
  }

  @Test
  void cardPreviewConfirmationAndJourneyReachCanonicalIngress() throws Exception {
    JsonNode catalog =
        body(
            client
                .get()
                .uri("/v1/context/intents")
                .header(
                    "X-Spider-Credential-Ref",
                    LocalDemoCanonicalCredentials.CREDENTIAL_REF)
                .exchange()
                .expectStatus()
                .isOk());
    JsonNode contract = catalog.path("items").get(0).path("intentContract");

    JsonNode preview =
        body(
            client
                .post()
                .uri("/v1/context/intents/resolve")
                .header(
                    "X-Spider-Credential-Ref",
                    LocalDemoCanonicalCredentials.CREDENTIAL_REF)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(contract)
                .exchange()
                .expectStatus()
                .isOk());
    assertEquals("ACCEPTED", preview.path("decision").asText());
    assertEquals(
        "CREDIT_RELEASE_DIAGNOSTIC_V1", preview.path("route").path("routeRef").asText());
    assertTrue(
        preview
            .path("contextJourney")
            .get(1)
            .path("summary")
            .asText()
            .contains("INVESTIGATE_CREDIT_RELEASE"));
    assertTrue(
        preview
            .path("contextJourney")
            .get(3)
            .path("summary")
            .asText()
            .contains("CREDIT_RELEASE_DIAGNOSTIC_V1"));

    JsonNode executed =
        body(
            client
                .post()
                .uri("/v1/context/executions")
                .header(
                    "X-Spider-Credential-Ref",
                    LocalDemoCanonicalCredentials.CREDENTIAL_REF)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(
                    Map.of(
                        "decisionId",
                        preview.path("decisionId").asText(),
                        "intentContract",
                        contract))
                .exchange()
                .expectStatus()
                .is2xxSuccessful());
    String executionId = executed.path("executionId").asText();
    assertNotNull(executionId);
    assertEquals("SUCCEEDED", executed.path("state").asText());

    client
        .get()
        .uri("/v1/context/executions/{id}", executionId)
        .header("X-Spider-Credential-Ref", LocalDemoCanonicalCredentials.CREDENTIAL_REF)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.contextJourney.length()")
        .isEqualTo(4)
        .jsonPath("$.executionId")
        .isEqualTo(executionId);

    client
        .get()
        .uri("/v1/console/executions/{id}/events", executionId)
        .header("X-Spider-Credential-Ref", LocalDemoCanonicalCredentials.CREDENTIAL_REF)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.items[?(@.eventType=='INTENT_CREATED')]")
        .isNotEmpty()
        .jsonPath("$.items[?(@.eventType=='INTENT_VALIDATED')]")
        .isNotEmpty()
        .jsonPath("$.items[?(@.eventType=='ROUTE_RESOLVED')]")
        .isNotEmpty();
  }

  private JsonNode body(WebTestClient.ResponseSpec response) throws Exception {
    byte[] bytes = response.expectBody().returnResult().getResponseBody();
    return mapper.readTree(bytes);
  }
}
