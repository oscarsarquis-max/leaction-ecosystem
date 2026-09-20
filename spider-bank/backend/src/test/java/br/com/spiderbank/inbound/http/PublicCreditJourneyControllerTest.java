package br.com.spiderbank.inbound.http;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import br.com.spiderbank.application.SpiderDecisionGateway;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.http.MediaType;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(
    properties = {
      "spiderbank.cors.allowed-origin=http://127.0.0.1:5190",
      "spiderbank.spider.application-secret=test-only",
      "spiderbank.customer-assertion.secret=test-assertion-secret"
    })
@Import(PublicCreditJourneyControllerTest.GatewayConfig.class)
class PublicCreditJourneyControllerTest {

  @Autowired MockMvc mvc;

  @Test
  void healthDoesNotExposeSecrets() throws Exception {
    mvc.perform(get("/api/health"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("UP"))
        .andExpect(jsonPath("$.satelliteId").value("spiderbank"))
        .andExpect(jsonPath("$.applicationSecret").doesNotExist());
  }

  @Test
  void contextIsSyntheticAndGoverned() throws Exception {
    mvc.perform(get("/api/credit/context"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.synthetic").value(true))
        .andExpect(jsonPath("$.sourceId").value("SPIDERBANK_WORKING_CAPITAL_SYNTHETIC_V1"))
        .andExpect(jsonPath("$.captureMethod").value("SERVER_REGISTRY"))
        .andExpect(jsonPath("$.objectiveCode").value("SEEK_WORKING_CAPITAL"));
  }

  @Test
  void confirmedJourneyReturnsSpiderImpediments() throws Exception {
    mvc.perform(
            post("/api/credit/journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .header("X-Correlation-ID", "corr-web-1")
                .header("Idempotency-Key", "idem-web-1")
                .content("{\"objectiveConfirmed\":true}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("ANALYSIS_BLOCKED"))
        .andExpect(jsonPath("$.creditDecision").value("NONE"))
        .andExpect(jsonPath("$.impediments.length()").value(7))
        .andExpect(jsonPath("$.technical.planId").value("WORKING_CAPITAL_DIAGNOSTIC_V1"));
  }

  @Test
  void demoSessionIssuesSyntheticAssertionWithoutAcceptingCustomerId() throws Exception {
    mvc.perform(
            post("/api/credit/demo-session")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"persona\":\"ok\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.synthetic").value(true))
        .andExpect(jsonPath("$.environment").value("TEST_DOUBLE"))
        .andExpect(jsonPath("$.subjectRef").value("cust-demo-ok"))
        .andExpect(jsonPath("$.assertion").exists())
        .andExpect(jsonPath("$.customerId").doesNotExist());
  }

  @Test
  void unconfirmedJourneyIsRejected() throws Exception {
    mvc.perform(
            post("/api/credit/journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    "{\"objectiveConfirmed\":false,\"correlationId\":\"corr-web-2\",\"idempotencyKey\":\"idem-web-2\"}"))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.errorCode").value("OBJECTIVE_NOT_CONFIRMED"))
        .andExpect(jsonPath("$.creditDecision").value("NONE"));
  }

  @TestConfiguration
  static class GatewayConfig {
    @Bean
    @Primary
    SpiderDecisionGateway spiderDecisionGateway() {
      return command -> {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("status", "PLAN_IMPEDED");
        body.put("decisionId", "spd-web");
        body.put("correlationId", command.correlationId());
        body.put("contextRef", "ctx-web");
        body.put("requiredAction", "PRESENT_PLAN_IMPEDIMENTS");
        body.put("explanation", "A Spider devolveu impedimentos. Isso não é recusa de crédito.");
        body.put("watermark", "DEMONSTRAÇÃO");
        body.put(
            "resultSummary",
            Map.of(
                "intent",
                "SEEK_WORKING_CAPITAL",
                "planId",
                "WORKING_CAPITAL_DIAGNOSTIC_V1",
                "providerDispatched",
                false,
                "impediments",
                List.of(
                    Map.of(
                        "sequence",
                        1,
                        "capabilityId",
                        "IDENTIFY_CUSTOMER",
                        "reason",
                        "sem cliente",
                        "availability",
                        "AVAILABLE"),
                    Map.of(
                        "sequence",
                        2,
                        "capabilityId",
                        "GET_CUSTOMER_PROFILE",
                        "reason",
                        "n/a",
                        "availability",
                        "NOT_AVAILABLE"),
                    Map.of(
                        "sequence",
                        3,
                        "capabilityId",
                        "CHECK_CUSTOMER_REGISTRATION",
                        "reason",
                        "n/a",
                        "availability",
                        "NOT_AVAILABLE"),
                    Map.of(
                        "sequence",
                        4,
                        "capabilityId",
                        "GET_CREDIT_PROFILE",
                        "reason",
                        "n/a",
                        "availability",
                        "NOT_AVAILABLE"),
                    Map.of(
                        "sequence",
                        5,
                        "capabilityId",
                        "FIND_ELIGIBLE_PRODUCTS",
                        "reason",
                        "n/a",
                        "availability",
                        "NOT_AVAILABLE"),
                    Map.of(
                        "sequence",
                        6,
                        "capabilityId",
                        "SIMULATE_WORKING_CAPITAL",
                        "reason",
                        "n/a",
                        "availability",
                        "NOT_AVAILABLE"),
                    Map.of(
                        "sequence",
                        7,
                        "capabilityId",
                        "PRESENT_OPTIONS",
                        "reason",
                        "n/a",
                        "availability",
                        "NOT_AVAILABLE"))));
        return SpiderDecisionGateway.Result.ok(body);
      };
    }
  }
}
