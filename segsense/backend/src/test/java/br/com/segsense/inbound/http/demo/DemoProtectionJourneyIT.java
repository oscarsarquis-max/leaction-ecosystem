package br.com.segsense.inbound.http.demo;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import br.com.segsense.application.demo.DemoJourneyRequestFingerprint;
import br.com.segsense.application.demo.DemoProtectionDecisionGateway;
import br.com.segsense.application.demo.DemoProtectionDecisionGateway.Item;
import br.com.segsense.application.demo.DemoProtectionDecisionGateway.Result;
import br.com.segsense.application.demo.GovernedDemoOrigin;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
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
import org.springframework.jdbc.core.JdbcTemplate;
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
  @Autowired JdbcTemplate jdbcTemplate;

  @Test
  void submitsSyntheticJourneyWithoutCallingMockDirectly() throws Exception {
    mockMvc
        .perform(
            post("/api/v1/public/demo/protection-journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Idempotency-Key", UUID.randomUUID().toString())
                .header("X-Correlation-ID", "33333333-3333-3333-3333-333333333333")
                .content(
                    "{\"declaredObjective\":\"UNDERSTAND_PROTECTION_OPTIONS\",\"declaredContext\":\"continuidade familiar com dependentes\",\"intentionConfirmed\":\"true\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.notIcatuProposal").value(true))
        .andExpect(jsonPath("$.demoSliceOnly").value(true))
        .andExpect(jsonPath("$.status").value("PRE_PROPOSAL_AVAILABLE"))
        .andExpect(jsonPath("$.spiderDecisionId").value("spd-test"))
        .andExpect(jsonPath("$.mockResultId").value("ill-test"))
        .andExpect(jsonPath("$.capabilityId").value("BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO"))
        .andExpect(jsonPath("$.satelliteContractVersion").value("1.1"))
        .andExpect(jsonPath("$.originProvenance.channel").value("SEGSENSE_PUBLIC_DEMO"))
        .andExpect(jsonPath("$.originProvenance.nonPersonal").value(true));
  }

  @Test
  void emptyPublicContextDoesNotChooseFamilySilently() throws Exception {
    mockMvc
        .perform(
            post("/api/v1/public/demo/protection-journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Idempotency-Key", UUID.randomUUID().toString())
                .content("{\"declaredObjective\":\"UNDERSTAND_PROTECTION_OPTIONS\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("MISSING_CONTEXT"))
        .andExpect(jsonPath("$.mockCalled").value(false))
        .andExpect(jsonPath("$.items").isEmpty());
  }

  @Test
  void labeledLegacyRouteKeepsFamilyFixture() throws Exception {
    mockMvc
        .perform(
            post("/api/v1/public/demo/legacy-protection-journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Idempotency-Key", UUID.randomUUID().toString())
                .content("{\"declaredObjective\":\"UNDERSTAND_FAMILY_PROTECTION_OPTIONS\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("PRE_PROPOSAL_AVAILABLE"))
        .andExpect(jsonPath("$.scenarioKey").value("SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1"));
  }

  @Test
  void replaysTheSameIdempotencyKey() throws Exception {
    String key = UUID.randomUUID().toString();
    String body =
        "{\"declaredObjective\":\"UNDERSTAND_PROTECTION_OPTIONS\",\"declaredContext\":\"continuidade familiar com dependentes\",\"intentionConfirmed\":\"true\"}";
    String first =
        mockMvc
            .perform(
                post("/api/v1/public/demo/protection-journeys")
                    .contentType(MediaType.APPLICATION_JSON)
                    .header("Idempotency-Key", key)
                    .content(body))
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
                .content(body))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.id").value(id));
    mockMvc
        .perform(get("/api/v1/public/demo/protection-journeys/" + id))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.demoSliceOnly").value(true));
  }

  @Test
  void sameKeyWithDifferentContextConflicts() throws Exception {
    String key = UUID.randomUUID().toString();
    mockMvc
        .perform(
            post("/api/v1/public/demo/protection-journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Idempotency-Key", key)
                .content(
                    "{\"declaredObjective\":\"UNDERSTAND_PROTECTION_OPTIONS\",\"declaredContext\":\"continuidade familiar\",\"intentionConfirmed\":\"true\"}"))
        .andExpect(status().isOk());
    mockMvc
        .perform(
            post("/api/v1/public/demo/protection-journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Idempotency-Key", key)
                .content(
                    "{\"declaredObjective\":\"UNDERSTAND_PROTECTION_OPTIONS\",\"declaredContext\":\"interrupção de renda\",\"intentionConfirmed\":\"true\"}"))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.code").value("IDEMPOTENCY_CONFLICT"))
        .andExpect(jsonPath("$.items").doesNotExist())
        .andExpect(jsonPath("$.mockResultId").doesNotExist())
        .andExpect(jsonPath("$.projectionJson").doesNotExist());
  }

  @Test
  void sameKeyWithDifferentIntentionConflicts() throws Exception {
    String key = UUID.randomUUID().toString();
    mockMvc
        .perform(
            post("/api/v1/public/demo/protection-journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Idempotency-Key", key)
                .content(
                    "{\"declaredObjective\":\"UNDERSTAND_PROTECTION_OPTIONS\",\"declaredContext\":\"continuidade familiar\",\"intentionConfirmed\":\"true\"}"))
        .andExpect(status().isOk());
    mockMvc
        .perform(
            post("/api/v1/public/demo/protection-journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Idempotency-Key", key)
                .content(
                    "{\"declaredObjective\":\"COMPARE_COVERAGE_GAPS\",\"declaredContext\":\"continuidade familiar\",\"intentionConfirmed\":\"true\"}"))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.code").value("IDEMPOTENCY_CONFLICT"));
  }

  @Test
  void existingRowWithoutFingerprintConflicts() throws Exception {
    String key = UUID.randomUUID().toString();
    String body =
        "{\"declaredObjective\":\"UNDERSTAND_PROTECTION_OPTIONS\",\"declaredContext\":\"continuidade familiar com dependentes\",\"intentionConfirmed\":\"true\"}";
    mockMvc
        .perform(
            post("/api/v1/public/demo/protection-journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Idempotency-Key", key)
                .content(body))
        .andExpect(status().isOk());
    jdbcTemplate.update(
        "UPDATE segsense.demo_protection_journey SET request_fingerprint = NULL WHERE idempotency_key_hash = ?",
        DemoJourneyRequestFingerprint.sha256(key));
    mockMvc
        .perform(
            post("/api/v1/public/demo/protection-journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Idempotency-Key", key)
                .content(body))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.code").value("IDEMPOTENCY_CONFLICT"));
  }

  @Test
  void resolvesGovernedUrlOnIsolatedFrontendPort() throws Exception {
    mockMvc
        .perform(
            post("/api/v1/public/demo/context-sources/resolve")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"url\":\"http://127.0.0.1:15178/demonstracao/fontes/continuidade-familiar\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.id").value("SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1"));
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

  @Test
  void resolvesGovernedFamilyUrl() throws Exception {
    mockMvc
        .perform(
            post("/api/v1/public/demo/context-sources/resolve")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"url\":\"http://127.0.0.1:5178/demonstracao/fontes/continuidade-familiar\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.id").value("SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1"))
        .andExpect(jsonPath("$.revoked").value(false));
  }

  @Test
  void rejectsRevokedAndPrivateUrls() throws Exception {
    mockMvc
        .perform(
            post("/api/v1/public/demo/context-sources/resolve")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"url\":\"http://127.0.0.1:5178/demonstracao/fontes/revogada\"}"))
        .andExpect(status().isConflict())
        .andExpect(jsonPath("$.code").value("REVOKED_CONTEXT_SOURCE"));
    mockMvc
        .perform(
            post("/api/v1/public/demo/context-sources/resolve")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"url\":\"http://169.254.169.254/latest/meta-data\"}"))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.code").value("INVALID_CONTEXT_URL"));
  }

  @Test
  void rejectsObviousPersonalData() throws Exception {
    mockMvc
        .perform(
            post("/api/v1/public/demo/protection-journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Idempotency-Key", UUID.randomUUID().toString())
                .content(
                    "{\"declaredObjective\":\"UNDERSTAND_PROTECTION_OPTIONS\",\"declaredContext\":\"email teste@example.com\",\"intentionConfirmed\":\"true\"}"))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.code").value("PERSONAL_DATA_NOT_ALLOWED"));
  }

  @Test
  void insufficientDeclaredContextDoesNotCallGatewayForMissingTheme() throws Exception {
    mockMvc
        .perform(
            post("/api/v1/public/demo/protection-journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Idempotency-Key", UUID.randomUUID().toString())
                .content(
                    "{\"declaredObjective\":\"UNDERSTAND_PROTECTION_OPTIONS\",\"declaredContext\":\"asdf\",\"intentionConfirmed\":\"true\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("MISSING_CONTEXT"))
        .andExpect(jsonPath("$.items").isEmpty());
  }

  @Test
  void homeQuoteWithoutAmountAsksQuestionsAndDoesNotInventPremium() throws Exception {
    mockMvc
        .perform(
            post("/api/v1/public/demo/protection-journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Idempotency-Key", UUID.randomUUID().toString())
                .content(
                    "{\"declaredIntention\":\"Quero contratar um seguro residencial\",\"declaredContext\":\"Houve incêndios nas proximidades\",\"intentionConfirmed\":\"true\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("MISSING_CONTEXT"))
        .andExpect(jsonPath("$.missingQuestions[0].code").value("dwelling_type"));
  }

  @Test
  void homeQuoteWithSyntheticInputsReturnsCalculatedPremium() throws Exception {
    mockMvc
        .perform(
            post("/api/v1/public/demo/protection-journeys")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Idempotency-Key", UUID.randomUUID().toString())
                .content(
                    "{\"declaredIntention\":\"Quero contratar um seguro residencial\",\"declaredContext\":\"Houve incêndios nas proximidades\",\"intentionConfirmed\":\"true\",\"dwellingType\":\"APARTMENT\",\"insuredAmountCents\":\"30000000\",\"coverPeriodMonths\":\"12\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("SIMULATED_QUOTE_AVAILABLE"))
        .andExpect(jsonPath("$.quoteReference").value("qte-test"))
        .andExpect(jsonPath("$.simulatedQuote.premiumAnnualCents").value(54000));
  }

  @TestConfiguration
  static class FakeGatewayConfig {
    @Bean
    @Primary
    DemoProtectionDecisionGateway demoProtectionDecisionGateway() {
      return command -> {
        if ("SIMULATE_HOME_QUOTE".equals(command.declaredObjective())) {
          if (command.contextAttributes() == null
              || !command.contextAttributes().containsKey("insuredAmountCents")) {
            return new Result(
                true,
                "MISSING_CONTEXT",
                "spd-missing",
                "Faltam dados sintéticos para calcular uma cotação simulada.",
                "SPIDER_SATELLITE_CONTRACT_V1",
                "DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO",
                false,
                null,
                null,
                null,
                List.of(),
                List.of(),
                Map.of(),
                "SATELLITE_CONTRACT_V1_1_THEN_CAPABILITY_RESOLUTION",
                "VALIDATION",
                "1.1",
                null,
                null,
                "PROVIDE_CONTEXT",
                Map.of(),
                List.of("dwelling_type", "insured_amount", "cover_period"));
          }
          Map<String, Object> quote = new LinkedHashMap<>();
          quote.put("premiumAnnualCents", 54000);
          quote.put("insuredAmountCents", 30000000);
          quote.put("coverPeriodMonths", 12);
          quote.put("dwellingType", "APARTMENT");
          quote.put("humanCalculation", "Prêmio anual simulado = capital declarado × 18 bps.");
          return new Result(
              true,
              "QUOTE_READY",
              "spd-quote",
              "Dados suficientes para pedir uma cotação simulada.",
              "SPIDER_SATELLITE_CONTRACT_V1",
              "SIMULAÇÃO DEMONSTRATIVA — SEM VALIDADE COMERCIAL — NÃO É OFERTA ICATU NEM CONTRATAÇÃO",
              true,
              "qte-test",
              "NON_BINDING_DEMO",
              "insurance-provider-mock",
              List.of(),
              List.of(),
              Map.of(),
              "SATELLITE_CONTRACT_V1_1_THEN_CAPABILITY_RESOLUTION",
              null,
              "1.1",
              "GENERATE_SYNTHETIC_HOME_QUOTE",
              "preq-quote",
              "PRESENT_SIMULATED_QUOTE",
              quote,
              List.of());
        }
        return new Result(
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
              "1.1",
              "BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO",
              "preq-test",
              "PRESENT_ILLUSTRATIVE_PRE_PROPOSAL",
              Map.of(),
              List.of());
      };
    }
  }
}
