package br.com.segsense.inbound.http.demo;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import br.com.segsense.application.demo.DemoProtectionDecisionGateway;
import br.com.segsense.application.demo.DemoProtectionDecisionGateway.Item;
import br.com.segsense.application.demo.DemoProtectionDecisionGateway.Result;
import br.com.segsense.application.demo.GovernedDemoOrigin;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
@Testcontainers
@ActiveProfiles("test")
@Import(DemoProtectionJourneyIT.FakeGatewayConfig.class)
class DemoProtectionJourneyIT {

  @Container
  @ServiceConnection
  static PostgreSQLContainer postgres = new PostgreSQLContainer("postgres:18.6");

  @Autowired MockMvc mockMvc;

  @Test
  void submitsSyntheticJourneyWithoutCallingMockDirectly() throws Exception {
    mockMvc
        .perform(
            post("/api/v1/public/demo/protection-journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Idempotency-Key", UUID.randomUUID().toString())
                .header("X-Correlation-ID", "33333333-3333-3333-3333-333333333333")
                .content("{\"declaredObjective\":\"UNDERSTAND_FAMILY_PROTECTION_OPTIONS\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.notIcatuProposal").value(true))
        .andExpect(jsonPath("$.demoSliceOnly").value(true))
        .andExpect(jsonPath("$.status").value("PRE_PROPOSAL_AVAILABLE"))
        .andExpect(jsonPath("$.spiderDecisionId").value("spd-test"))
        .andExpect(jsonPath("$.mockResultId").value("ill-test"))
        .andExpect(jsonPath("$.capabilityId").value("BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO"))
        .andExpect(jsonPath("$.satelliteContractVersion").value("1.0"))
        .andExpect(jsonPath("$.originProvenance.channel").value("SEGSENSE_PUBLIC_DEMO"))
        .andExpect(jsonPath("$.originProvenance.nonPersonal").value(true));
  }

  @Test
  void replaysTheSameIdempotencyKey() throws Exception {
    String key = UUID.randomUUID().toString();
    String first =
        mockMvc
            .perform(
                post("/api/v1/public/demo/protection-journeys")
                    .contentType(MediaType.APPLICATION_JSON)
                    .header("Idempotency-Key", key)
                    .content("{\"declaredObjective\":\"UNDERSTAND_FAMILY_PROTECTION_OPTIONS\"}"))
            .andExpect(status().isOk())
            .andReturn()
            .getResponse()
            .getContentAsString();
    String id = first.replaceAll(".*\"id\":\"([^\"]+)\".*", "$1");
    mockMvc
        .perform(
            post("/api/v1/public/demo/protection-journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Idempotency-Key", key)
                .content("{\"declaredObjective\":\"UNDERSTAND_FAMILY_PROTECTION_OPTIONS\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.id").value(id));
    mockMvc
        .perform(get("/api/v1/public/demo/protection-journeys/" + id))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.demoSliceOnly").value(true));
  }

  @Test
  void missingIdempotencyKeyIsRejected() throws Exception {
    mockMvc
        .perform(
            post("/api/v1/public/demo/protection-journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"declaredObjective\":\"UNDERSTAND_FAMILY_PROTECTION_OPTIONS\"}"))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.code").value("IDEMPOTENCY_KEY_REQUIRED"));
  }

  @Test
  void unknownJourneyIsNotFound() throws Exception {
    mockMvc
        .perform(get("/api/v1/public/demo/protection-journeys/" + UUID.randomUUID()))
        .andExpect(status().isNotFound());
  }

  @TestConfiguration
  static class FakeGatewayConfig {
    @Bean
    @Primary
    DemoProtectionDecisionGateway demoProtectionDecisionGateway() {
      return command ->
          new Result(
              true,
              "PRE_PROPOSAL_READY",
              "spd-test",
              "Decisão de teste.",
              "SPIDER_DETERMINISTIC_DEMO",
              "DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO",
              true,
              "ill-test",
              "ILLUSTRATIVE_NOT_ICATU_CONTRACT",
              "SEGSENSE_PROVIDER_MOCK",
              List.of(new Item("STEP", "Revisar contexto", "JOURNEY_STEP", true)),
              List.of("Confirmar com a seguradora autorizada."),
              GovernedDemoOrigin.snapshot(),
              "SATELLITE_CONTRACT_V1_THEN_CAPABILITY_RESOLUTION",
              null,
              "1.0",
              "BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO",
              "preq-test",
              "PRESENT_ILLUSTRATIVE_PRE_PROPOSAL");
    }
  }
}
