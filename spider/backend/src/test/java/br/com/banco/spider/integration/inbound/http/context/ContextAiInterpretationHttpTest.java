package br.com.banco.spider.integration.inbound.http.context;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
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

@SpringBootTest(
    properties = {
      "spider.context.ai.enabled=true",
      "spider.context.ai.provider=scripted",
      "spider.context.ai.scripted-enabled=true"
    })
@AutoConfigureWebTestClient(timeout = "PT30S")
@ActiveProfiles("local-demo")
class ContextAiInterpretationHttpTest {

  @Autowired WebTestClient client;
  @Autowired ObjectMapper mapper;

  @Test
  void explicitNaturalLanguageIntentUsesSameGuardRouterAndConfirmation() throws Exception {
    JsonNode catalog = get("/v1/context/intents");
    assertTrue(catalog.path("aiEnabled").asBoolean());
    assertEquals("ACTIVE", catalog.path("aiState").asText());
    assertEquals("scripted-evidence", catalog.path("aiProvider").asText());

    JsonNode ai =
        interpret(
            "Minha proposta 12345 foi aprovada, mas o crédito ainda não foi liberado.");
    assertEquals("SUCCEEDED", ai.path("status").asText());
    JsonNode decision = ai.path("decision");
    assertEquals("ACCEPTED", decision.path("decision").asText());
    assertEquals(
        "INVESTIGATE_CREDIT_RELEASE",
        decision.path("intentContract").path("intent").asText());
    assertEquals(
        "NATURAL_LANGUAGE",
        decision.path("intentContract").path("provenance").path("source").asText());
    assertFalse(
        decision.path("intentContract").path("constraints").path("mutationAllowed").asBoolean());
    assertEquals("12345", decision.path("intentContract").path("entities").path("proposalId").asText());
    assertEquals(
        "CREDIT_RELEASE_DIAGNOSTIC_V1",
        decision.path("route").path("routeRef").asText());
    assertEquals(
        "CREDIT_RELEASE_INVESTIGATION_PLAN_V1",
        decision.path("executionPlan").path("planType").asText());
    assertEquals(
        "CREDIT_RELEASE_DIAGNOSTIC",
        decision.path("capabilities").get(0).path("capabilityId").asText());
    assertEquals(8, decision.path("contextJourney").size());
    assertEquals("ai-interpreted", decision.path("contextJourney").get(1).path("id").asText());
    assertTrue(decision.path("executionId").isNull());

    JsonNode card = catalog.path("items").get(0).path("intentContract");
    JsonNode cardDecision = resolve(card);
    assertEquals(
        cardDecision.path("route").path("routeRef").asText(),
        decision.path("route").path("routeRef").asText());

    JsonNode executed =
        post(
            "/v1/context/executions",
            Map.of(
                "decisionId",
                decision.path("decisionId").asText(),
                "intentContract",
                decision.path("intentContract")));
    String executionId = executed.path("executionId").asText();
    assertFalse(executionId.isBlank());
    getResponse("/v1/console/executions/" + executionId + "/events")
        .expectBody()
        .jsonPath("$.items[?(@.eventType=='AI_INTERPRETATION_SUCCEEDED')]")
        .isNotEmpty();
  }

  @Test
  void missingAmbiguousAndUnsupportedNeverReceiveRoute() throws Exception {
    JsonNode missing =
        interpret("Minha proposta foi aprovada, mas o crédito ainda não foi liberado.");
    assertEquals("MISSING_CONTEXT", missing.path("status").asText());
    assertEquals(
        "proposalId",
        missing.path("interpretation").path("missingContext").get(0).asText());
    assertTrue(missing.path("decision").path("route").isNull());
    getResponse(
            "/v1/console/executions/"
                + missing.path("decision").path("decisionId").asText()
                + "/events")
        .expectBody()
        .jsonPath("$.items[?(@.eventType=='EXECUTION_PLAN_REJECTED')]")
        .isNotEmpty();
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
                missing.path("decision").path("decisionId").asText(),
                "intentContract",
                missing.path("decision").path("intentContract")))
        .exchange()
        .expectStatus()
        .isEqualTo(422);

    JsonNode ambiguous = interpret("Quero saber o que aconteceu com o cliente João.");
    assertEquals("AMBIGUOUS", ambiguous.path("status").asText());
    assertTrue(ambiguous.path("decision").isNull());
    assertEquals(3, ambiguous.path("interpretation").path("candidateIntents").size());

    JsonNode unsupported = interpret("Quero comprar passagens para Paris.");
    assertEquals("UNSUPPORTED_INTENT", unsupported.path("status").asText());
    assertTrue(unsupported.path("decision").isNull());
    assertNull(unsupported.path("interpretation").path("intent").textValue());
  }

  @Test
  void workingCapitalProducesPartialPlanAndNeverReachesExecution() throws Exception {
    JsonNode result = interpret("Preciso de R$ 50 mil para reforçar meu estoque.");
    JsonNode decision = result.path("decision");

    assertEquals("SUCCEEDED", result.path("status").asText());
    assertEquals(
        "SEEK_WORKING_CAPITAL",
        decision.path("intentContract").path("intent").asText());
    assertEquals(
        "INVENTORY",
        decision.path("intentContract").path("entities").path("purpose").asText());
    assertEquals(
        "50000",
        decision.path("intentContract").path("entities").path("amount").asText());
    assertEquals(
        "WORKING_CAPITAL_DIAGNOSTIC_V1",
        decision.path("executionPlan").path("planType").asText());
    assertEquals(
        "PARTIALLY_AVAILABLE",
        decision.path("executionPlan").path("status").asText());
    assertEquals(7, decision.path("capabilities").size());
    assertEquals("RESOLVED", decision.path("capabilities").get(0).path("status").asText());
    assertEquals(
        "UNAVAILABLE", decision.path("capabilities").get(1).path("status").asText());
    assertTrue(decision.path("route").isNull());
    assertTrue(decision.path("executionId").isNull());
    assertFalse(decision.path("createdAt").isNull());
    assertFalse(decision.path("decisionId").asText().isBlank());
    assertFalse(decision.path("executionPlan").path("planId").asText().isBlank());
    assertEquals(
        "IDENTIFY_CUSTOMER",
        decision.path("capabilities").get(0).path("capabilityId").asText());
    assertEquals(
        "AUTHENTICATED_CONTEXT_CUSTOMER_V1",
        decision.path("capabilities").get(0).path("selectedRoute").path("routeRef").asText());
    assertTrue(decision.path("capabilities").get(1).path("selectedRoute").isNull());

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
                decision.path("decisionId").asText(),
                "intentContract",
                decision.path("intentContract")))
        .exchange()
        .expectStatus()
        .isEqualTo(422)
        .expectBody()
        .jsonPath("$.reasonCode")
        .isEqualTo("EXECUTION_PLAN_PARTIALLY_AVAILABLE");

    getResponse(
            "/v1/console/executions/"
                + decision.path("decisionId").asText()
                + "/events")
        .expectBody()
        .jsonPath("$.items[?(@.eventType=='EXECUTION_PLAN_RESOLVED')]")
        .isNotEmpty()
        .jsonPath("$.items[?(@.eventType=='CAPABILITY_UNAVAILABLE')]")
        .isNotEmpty();
  }

  @Test
  void sensitiveValuesAreRedactedBeforeProviderAndAuditView() throws Exception {
    JsonNode result =
        interpret("Verifique a proposta 12345 token=segredo Bearer abc.def");
    String safe = result.path("requestedObjective").asText();
    assertFalse(safe.contains("segredo"));
    assertFalse(safe.contains("abc.def"));
    assertEquals(
        2, result.path("interpretation").path("redactedFieldsCount").asInt());
  }

  private JsonNode interpret(String objective) throws Exception {
    return post("/v1/context/interpretations", Map.of("objective", objective));
  }

  private JsonNode resolve(JsonNode contract) throws Exception {
    return post("/v1/context/intents/resolve", contract);
  }

  private JsonNode get(String uri) throws Exception {
    return body(getResponse(uri));
  }

  private WebTestClient.ResponseSpec getResponse(String uri) {
    return client
        .get()
        .uri(uri)
        .header(
            "X-Spider-Credential-Ref",
            LocalDemoCanonicalCredentials.CREDENTIAL_REF)
        .exchange()
        .expectStatus()
        .isOk();
  }

  private JsonNode post(String uri, Object payload) throws Exception {
    return body(
        client
            .post()
            .uri(uri)
            .header(
                "X-Spider-Credential-Ref",
                LocalDemoCanonicalCredentials.CREDENTIAL_REF)
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(payload)
            .exchange()
            .expectStatus()
            .isOk());
  }

  private JsonNode body(WebTestClient.ResponseSpec response) throws Exception {
    byte[] bytes = response.expectBody().returnResult().getResponseBody();
    return mapper.readTree(bytes);
  }
}
