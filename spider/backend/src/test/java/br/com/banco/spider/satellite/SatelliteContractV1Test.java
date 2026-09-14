package br.com.banco.spider.satellite;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import br.com.banco.spider.config.SatelliteContractProperties;
import br.com.banco.spider.config.SatelliteContractProperties.ProviderEntry;
import br.com.banco.spider.config.SatelliteContractProperties.SatelliteEntry;
import br.com.banco.spider.satellite.application.SatelliteInteractionService;
import br.com.banco.spider.satellite.application.SatelliteRegistry;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ResultItem;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextBlock;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextSnapshot;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Objective;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Provenance;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Mono;

public class SatelliteContractV1Test {

  private ProviderCapabilityPort providers;
  private SatelliteInteractionService service;

  @BeforeEach
  void setUp() {
    providers = mock(ProviderCapabilityPort.class);
    service = new SatelliteInteractionService(new SatelliteRegistry(properties()), providers, null);
  }

  @Test
  void validExperienceDispatchesCapability() {
    when(providers.execute(any()))
        .thenReturn(
            Mono.just(
                new ExecutionResult(
                    true,
                    "COMPLETED",
                    "preq-1",
                    "insurance-provider-mock",
                    "ill-1",
                    "ILLUSTRATIVE_NOT_ICATU_CONTRACT",
                    SatelliteContractV1.WATERMARK,
                    List.of(new ResultItem("STEP", "Revisar", "JOURNEY_STEP", true)),
                    List.of("Pendência"))));
    var outcome = service.interact("segsense", request("UNDERSTAND_FAMILY_PROTECTION_OPTIONS", "idem-valid-1")).block();
    assertEquals(200, outcome.status());
    assertEquals("READY", outcome.body().get("status"));
    String explanation = String.valueOf(outcome.body().get("explanation"));
    assertTrue(explanation.contains("regras explícitas"));
    assertTrue(explanation.contains("continuidade familiar"));
    assertTrue(explanation.contains("entender opções ilustrativas de proteção"));
    assertTrue(explanation.contains("provedor ilustrativo"));
    assertFalse(explanation.contains("family_continuity"));
    assertFalse(explanation.contains("UNDERSTAND_FAMILY_PROTECTION_OPTIONS"));
    assertFalse(explanation.contains("UNDERSTAND_PROTECTION_OPTIONS"));
    assertFalse(explanation.contains(SatelliteContractV1.ILLUSTRATIVE_CAPABILITY));
    assertFalse(explanation.contains("scenarioKey"));
    assertFalse(explanation.contains("|"));
    assertFalse(explanation.toLowerCase().contains("compreendeu"));
    assertFalse(explanation.toLowerCase().contains("interpretou"));
    assertFalse(explanation.toLowerCase().contains("personalizou"));
    assertEquals("SATELLITE_GOVERNED", ((Map<?, ?>) outcome.body().get("originProvenance")).get("sourceType"));
    assertFalse(outcome.body().containsKey("planId"));
    assertFalse(outcome.body().containsKey("executionId"));
    verify(providers).execute(any());
  }

  @Test
  void unknownSatelliteIsUnauthorized() {
    var outcome = service.interact("unknown", request("UNDERSTAND_FAMILY_PROTECTION_OPTIONS", "idem-unknown")).block();
    assertEquals(403, outcome.status());
    assertEquals("UNAUTHORIZED_SATELLITE", outcome.errorCode());
    verify(providers, never()).execute(any());
  }

  @Test
  void spoofedSatelliteIdIsRejected() {
    SatelliteInteractionRequest spoofed =
        new SatelliteInteractionRequest(
            "1.0",
            "msg-spoof",
            "11111111-1111-1111-1111-111111111111",
            "insurance-provider-mock",
            "EXPERIENCE",
            "REQUEST_DECISION",
            "2026-09-13T12:00:00Z",
            "idem-spoof-1",
            SatelliteContractV1.PURPOSE_INSURANCE,
            new Objective("UNDERSTAND_FAMILY_PROTECTION_OPTIONS", "SATELLITE_GOVERNED", "2026-09-13T12:00:00Z"),
            governedContext("SEGSENSE_PUBLIC_DEMO"),
            "INTERNAL",
            "SYNC",
            Map.of());
    var outcome = service.interact("segsense", spoofed).block();
    assertEquals(403, outcome.status());
    verify(providers, never()).execute(any());
  }

  @Test
  void invalidVersionFailsClosed() {
    SatelliteInteractionRequest badVersion =
        new SatelliteInteractionRequest(
            "9.0",
            "msg-ver",
            "11111111-1111-1111-1111-111111111111",
            "segsense",
            "EXPERIENCE",
            "REQUEST_DECISION",
            "2026-09-13T12:00:00Z",
            "idem-version",
            SatelliteContractV1.PURPOSE_INSURANCE,
            new Objective("UNDERSTAND_FAMILY_PROTECTION_OPTIONS", "SATELLITE_GOVERNED", "2026-09-13T12:00:00Z"),
            governedContext("SEGSENSE_PUBLIC_DEMO"),
            "INTERNAL",
            "SYNC",
            Map.of());
    var outcome = service.interact("segsense", badVersion).block();
    assertEquals(400, outcome.status());
    assertEquals("INVALID_CONTRACT_VERSION", outcome.errorCode());
  }

  @Test
  void pageContextIsNotAcceptedAsGoverned() {
    SatelliteInteractionRequest page =
        requestWithProvenance("PAGE_CONTEXT", "idem-page-ctx");
    var outcome = service.interact("segsense", page).block();
    assertEquals(400, outcome.status());
    verify(providers, never()).execute(any());
  }

  @Test
  void missingContextFailsBeforeProvider() {
    SatelliteInteractionRequest missing =
        new SatelliteInteractionRequest(
            "1.0",
            "msg-miss",
            "11111111-1111-1111-1111-111111111111",
            "segsense",
            "EXPERIENCE",
            "REQUEST_DECISION",
            "2026-09-13T12:00:00Z",
            "idem-missing-ctx",
            SatelliteContractV1.PURPOSE_INSURANCE,
            new Objective("UNDERSTAND_FAMILY_PROTECTION_OPTIONS", "SATELLITE_GOVERNED", "2026-09-13T12:00:00Z"),
            null,
            "INTERNAL",
            "SYNC",
            Map.of());
    var outcome = service.interact("segsense", missing).block();
    assertEquals(400, outcome.status());
    assertEquals("MISSING_CONTEXT", outcome.errorCode());
    verify(providers, never()).execute(any());
  }

  @Test
  void rejectedObjectiveDoesNotCallProvider() {
    var outcome = service.interact("segsense", request("REQUEST_BINDING_QUOTE", "idem-reject-1")).block();
    assertEquals("REJECTED", outcome.body().get("status"));
    String explanation = String.valueOf(outcome.body().get("explanation"));
    assertEquals(
        "A Spider recusou a intenção confirmada: não está entre as permitidas nesta demonstração. Nenhum encaminhamento ao provedor foi feito.",
        explanation);
    assertFalse(explanation.toLowerCase().contains("compreendeu"));
    assertFalse(explanation.toLowerCase().contains("interpretou"));
    verify(providers, never()).execute(any());
  }

  @Test
  void providerFailureIsDistinctStatus() {
    when(providers.execute(any())).thenReturn(Mono.just(ExecutionResult.unavailable()));
    var outcome = service.interact("segsense", request("UNDERSTAND_FAMILY_PROTECTION_OPTIONS", "idem-unavail")).block();
    assertEquals("PROVIDER_UNAVAILABLE", outcome.body().get("status"));
    String explanation = String.valueOf(outcome.body().get("explanation"));
    assertEquals("A Spider validou o satélite, mas o executor da capability não respondeu.", explanation);
    assertFalse(explanation.toLowerCase().contains("compreendeu"));
  }

  @Test
  void replaySameKeyKeepsDecisionId() {
    when(providers.execute(any()))
        .thenReturn(Mono.just(ExecutionResult.unavailable()));
    var first = service.interact("segsense", request("UNDERSTAND_FAMILY_PROTECTION_OPTIONS", "idem-replay")).block();
    var second = service.interact("segsense", request("UNDERSTAND_FAMILY_PROTECTION_OPTIONS", "idem-replay")).block();
    assertEquals(first.body().get("decisionId"), second.body().get("decisionId"));
  }

  @Test
  void sameKeyDifferentContextConflicts() {
    when(providers.execute(any())).thenReturn(Mono.just(ExecutionResult.unavailable()));
    service.interact("segsense", request("UNDERSTAND_FAMILY_PROTECTION_OPTIONS", "idem-conflict")).block();
    var conflict =
        service.interact("segsense", requestWithChannel("OTHER_CHANNEL", "idem-conflict")).block();
    assertEquals(409, conflict.status());
    assertEquals("IDEMPOTENCY_CONFLICT", conflict.errorCode());
  }

  @Test
  void changingObjectiveWithNewKeyAltersDecision() {
    when(providers.execute(any())).thenReturn(Mono.just(ExecutionResult.unavailable()));
    var allowed = service.interact("segsense", request("UNDERSTAND_FAMILY_PROTECTION_OPTIONS", "idem-obj-a")).block();
    var rejected = service.interact("segsense", request("REQUEST_BINDING_QUOTE", "idem-obj-b")).block();
    assertEquals("PROVIDER_UNAVAILABLE", allowed.body().get("status"));
    assertEquals("REJECTED", rejected.body().get("status"));
    assertNotEquals(allowed.body().get("decisionId"), rejected.body().get("decisionId"));
  }

  @Test
  void experienceCannotExecuteCapability() {
    SatelliteInteractionRequest execute =
        new SatelliteInteractionRequest(
            "1.0",
            "msg-exec",
            "11111111-1111-1111-1111-111111111111",
            "segsense",
            "EXPERIENCE",
            "EXECUTE_CAPABILITY",
            "2026-09-13T12:00:00Z",
            "idem-execute",
            SatelliteContractV1.PURPOSE_INSURANCE,
            new Objective("UNDERSTAND_FAMILY_PROTECTION_OPTIONS", "SATELLITE_GOVERNED", "2026-09-13T12:00:00Z"),
            governedContext("SEGSENSE_PUBLIC_DEMO"),
            "INTERNAL",
            "SYNC",
            Map.of());
    var outcome = service.interact("segsense", execute).block();
    assertEquals(403, outcome.status());
    verify(providers, never()).execute(any());
  }

  @Test
  void providerRequestDoesNotCarryOriginSnapshot() {
    when(providers.execute(any()))
        .thenAnswer(
            invocation -> {
              ProviderCapabilityPort.ExecutionRequest sent = invocation.getArgument(0);
              assertEquals("SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1", sent.scenarioKey());
              assertEquals(SatelliteContractV1.ILLUSTRATIVE_CAPABILITY, sent.capabilityId());
              return Mono.just(ExecutionResult.unavailable());
            });
    service.interact("segsense", request("UNDERSTAND_FAMILY_PROTECTION_OPTIONS", "idem-minimise")).block();
  }

  @Test
  void missingThemeStatusDoesNotCallProvider() {
    var outcome =
        service.interact("segsense", requestWithConstraint("missing_context", "idem-missing-theme")).block();
    assertEquals(200, outcome.status());
    assertEquals("MISSING_CONTEXT", outcome.body().get("status"));
    assertEquals(List.of("theme"), outcome.body().get("missingContext"));
    verify(providers, never()).execute(any());
  }

  @Test
  void unresolvedConflictIsAmbiguousWithoutProvider() {
    var outcome =
        service.interact("segsense", requestWithConstraint("unresolved_conflict", "idem-ambiguous")).block();
    assertEquals("AMBIGUOUS", outcome.body().get("status"));
    verify(providers, never()).execute(any());
  }

  @Test
  void differentSourceAndIntentionChangeScenarioKey() {
    when(providers.execute(any()))
        .thenAnswer(
            invocation -> {
              ProviderCapabilityPort.ExecutionRequest sent = invocation.getArgument(0);
              return Mono.just(ExecutionResult.unavailable());
            });
    service
        .interact(
            "segsense",
            requestForSource("UNDERSTAND_PROTECTION_OPTIONS", "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1", "idem-sk-a"))
        .block();
    service
        .interact(
            "segsense",
            requestForSource("COMPARE_COVERAGE_GAPS", "SEGSENSE_INCOME_INTERRUPTION_SYNTHETIC_V1", "idem-sk-b"))
        .block();
    org.mockito.ArgumentCaptor<ProviderCapabilityPort.ExecutionRequest> captor =
        org.mockito.ArgumentCaptor.forClass(ProviderCapabilityPort.ExecutionRequest.class);
    verify(providers, org.mockito.Mockito.times(2)).execute(captor.capture());
    assertEquals(
        "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1|UNDERSTAND_PROTECTION_OPTIONS",
        captor.getAllValues().get(0).scenarioKey());
    assertEquals(
        "SEGSENSE_INCOME_INTERRUPTION_SYNTHETIC_V1|COMPARE_COVERAGE_GAPS",
        captor.getAllValues().get(1).scenarioKey());
    assertNotEquals(captor.getAllValues().get(0).scenarioKey(), captor.getAllValues().get(1).scenarioKey());
  }

  @Test
  void declaredContextOn11DispatchesDistinctScenario() {
    when(providers.execute(any()))
        .thenReturn(
            Mono.just(
                new ExecutionResult(
                    true,
                    "COMPLETED",
                    "preq-decl",
                    "insurance-provider-mock",
                    "ill-decl",
                    "ILLUSTRATIVE_NOT_ICATU_CONTRACT",
                    SatelliteContractV1.WATERMARK,
                    List.of(new ResultItem("STEP", "Revisar", "JOURNEY_STEP", true)),
                    List.of("Pendência"))));
    var outcome =
        service
            .interact(
                "segsense",
                declaredRequest(
                    "UNDERSTAND_PROTECTION_OPTIONS",
                    "SEGSENSE_DECLARED_FAMILY_CONTINUITY_V1",
                    "family_continuity",
                    "idem-decl-a"))
            .block();
    org.mockito.ArgumentCaptor<ProviderCapabilityPort.ExecutionRequest> captor =
        org.mockito.ArgumentCaptor.forClass(ProviderCapabilityPort.ExecutionRequest.class);
    verify(providers).execute(captor.capture());
    assertEquals(
        "SEGSENSE_DECLARED_FAMILY_CONTINUITY_V1|UNDERSTAND_PROTECTION_OPTIONS",
        captor.getValue().scenarioKey());
    String explanation = String.valueOf(outcome.body().get("explanation"));
    assertTrue(explanation.contains("relato declarado"));
    assertTrue(explanation.contains("continuidade familiar"));
    assertFalse(explanation.contains("SEGSENSE_DECLARED_FAMILY_CONTINUITY_V1"));
    assertFalse(explanation.contains("BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO"));
    assertFalse(explanation.contains("UNDERSTAND_PROTECTION_OPTIONS"));
    assertFalse(explanation.toLowerCase().contains("interpretou"));
    assertEquals("1.1", outcome.body().get("contractVersion"));
    Map<?, ?> origin = (Map<?, ?>) outcome.body().get("originProvenance");
    assertEquals("USER_DECLARED", origin.get("sourceType"));
    assertTrue(origin.get("contributions") instanceof List<?>);
  }

  @Test
  void combinationOn11KeepsBothContributions() {
    when(providers.execute(any())).thenReturn(Mono.just(ExecutionResult.unavailable()));
    var outcome = service.interact("segsense", combinationRequest("idem-both-1")).block();
    assertEquals(200, outcome.status());
    Map<?, ?> origin = (Map<?, ?>) outcome.body().get("originProvenance");
    List<?> contributions = (List<?>) origin.get("contributions");
    assertEquals(2, contributions.size());
    org.mockito.ArgumentCaptor<ProviderCapabilityPort.ExecutionRequest> captor =
        org.mockito.ArgumentCaptor.forClass(ProviderCapabilityPort.ExecutionRequest.class);
    verify(providers).execute(captor.capture());
    assertEquals(
        "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1|UNDERSTAND_PROTECTION_OPTIONS",
        captor.getValue().scenarioKey());
  }

  @Test
  void userDeclaredIsRejectedOnV1() {
    SatelliteInteractionRequest declaredOnV1 =
        new SatelliteInteractionRequest(
            "1.0",
            "msg-decl-v1",
            "11111111-1111-1111-1111-111111111111",
            "segsense",
            "EXPERIENCE",
            "REQUEST_DECISION",
            "2026-09-14T15:01:00Z",
            "idem-decl-v1",
            SatelliteContractV1.PURPOSE_INSURANCE,
            new Objective("UNDERSTAND_PROTECTION_OPTIONS", "USER_DECLARED", "2026-09-14T15:01:02Z"),
            new ContextBlock(
                null,
                new ContextSnapshot(
                    "1.0",
                    "INTERNAL",
                    true,
                    new Provenance(
                        "USER_DECLARED",
                        "SEGSENSE_DECLARED_FAMILY_CONTINUITY_V1",
                        "2026-09-14T15:01:00Z",
                        "SATELLITE_DECLARED",
                        "DECLARED"),
                    Map.of("channel", "SEGSENSE_PUBLIC_DEMO", "theme", "family_continuity"))),
            "INTERNAL",
            "SYNC",
            Map.of());
    var outcome = service.interact("segsense", declaredOnV1).block();
    assertEquals(400, outcome.status());
    verify(providers, never()).execute(any());
  }

  private static SatelliteInteractionRequest declaredRequest(
      String objective, String sourceId, String theme, String key) {
    Map<String, String> attributes = new LinkedHashMap<>();
    attributes.put("channel", "SEGSENSE_PUBLIC_DEMO");
    attributes.put("theme", theme);
    attributes.put("constraint", "no_quote");
    SatelliteInteractionRequest.Contribution declared =
        new SatelliteInteractionRequest.Contribution(
            "VISITOR_DECLARED",
            "USER_DECLARED",
            sourceId,
            "2026-09-14T15:01:00Z",
            "SATELLITE_DECLARED",
            "DECLARED",
            true,
            Map.of("theme", theme));
    ContextSnapshot snapshot =
        new ContextSnapshot(
            "1.1",
            "INTERNAL",
            true,
            new Provenance("USER_DECLARED", sourceId, "2026-09-14T15:01:00Z", "SATELLITE_DECLARED", "DECLARED"),
            attributes,
            List.of(declared),
            "VISITOR_DECLARED");
    return new SatelliteInteractionRequest(
        "1.1",
        "msg-" + key,
        "11111111-1111-1111-1111-111111111111",
        "segsense",
        "EXPERIENCE",
        "REQUEST_DECISION",
        "2026-09-14T15:01:00Z",
        key,
        SatelliteContractV1.PURPOSE_INSURANCE,
        new Objective(objective, "USER_DECLARED", "2026-09-14T15:01:02Z"),
        new ContextBlock(null, snapshot),
        "INTERNAL",
        "SYNC",
        Map.of());
  }

  private static SatelliteInteractionRequest combinationRequest(String key) {
    Map<String, String> attributes = new LinkedHashMap<>();
    attributes.put("channel", "SEGSENSE_PUBLIC_DEMO");
    attributes.put("theme", "family_continuity");
    attributes.put("constraint", "no_quote");
    SatelliteInteractionRequest.Contribution governed =
        new SatelliteInteractionRequest.Contribution(
            "GOVERNED_SOURCE",
            "SATELLITE_GOVERNED",
            "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1",
            "2026-09-13T12:00:00Z",
            "SERVER_REGISTRY",
            "GOVERNED",
            true,
            Map.of("theme", "family_continuity", "situation", "dependents_need_continuity"));
    SatelliteInteractionRequest.Contribution declared =
        new SatelliteInteractionRequest.Contribution(
            "VISITOR_DECLARED",
            "USER_DECLARED",
            "SEGSENSE_DECLARED_FAMILY_CONTINUITY_V1",
            "2026-09-14T15:03:00Z",
            "SATELLITE_DECLARED",
            "DECLARED",
            true,
            Map.of("theme", "family_continuity"));
    ContextSnapshot snapshot =
        new ContextSnapshot(
            "1.1",
            "INTERNAL",
            true,
            new Provenance(
                "USER_DECLARED",
                "SEGSENSE_DECLARED_FAMILY_CONTINUITY_V1",
                "2026-09-14T15:03:00Z",
                "SATELLITE_DECLARED",
                "DECLARED"),
            attributes,
            List.of(governed, declared),
            "BOTH");
    return new SatelliteInteractionRequest(
        "1.1",
        "msg-" + key,
        "11111111-1111-1111-1111-111111111111",
        "segsense",
        "EXPERIENCE",
        "REQUEST_DECISION",
        "2026-09-14T15:03:00Z",
        key,
        SatelliteContractV1.PURPOSE_INSURANCE,
        new Objective("UNDERSTAND_PROTECTION_OPTIONS", "USER_DECLARED", "2026-09-14T15:03:04Z"),
        new ContextBlock(null, snapshot),
        "INTERNAL",
        "SYNC",
        Map.of());
  }

  private static SatelliteInteractionRequest request(String objective, String key) {
    return requestWithChannel("SEGSENSE_PUBLIC_DEMO", key, objective);
  }

  private static SatelliteInteractionRequest requestWithConstraint(String constraint, String key) {
    Map<String, String> attributes = new LinkedHashMap<>();
    attributes.put("channel", "SEGSENSE_PUBLIC_DEMO");
    attributes.put("constraint", constraint);
    ContextSnapshot snapshot =
        new ContextSnapshot(
            "1.0",
            "INTERNAL",
            true,
            new Provenance(
                "SATELLITE_GOVERNED",
                "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1",
                "2026-09-13T12:00:00Z",
                "SERVER_REGISTRY",
                "GOVERNED"),
            attributes);
    return new SatelliteInteractionRequest(
        "1.0",
        "msg-" + key,
        "11111111-1111-1111-1111-111111111111",
        "segsense",
        "EXPERIENCE",
        "REQUEST_DECISION",
        "2026-09-13T12:00:00Z",
        key,
        SatelliteContractV1.PURPOSE_INSURANCE,
        new Objective("UNDERSTAND_FAMILY_PROTECTION_OPTIONS", "SATELLITE_GOVERNED", "2026-09-13T12:00:00Z"),
        new ContextBlock(null, snapshot),
        "INTERNAL",
        "SYNC",
        Map.of());
  }

  private static SatelliteInteractionRequest requestForSource(String objective, String sourceId, String key) {
    Map<String, String> attributes = new LinkedHashMap<>();
    attributes.put("channel", "SEGSENSE_PUBLIC_DEMO");
    ContextSnapshot snapshot =
        new ContextSnapshot(
            "1.0",
            "INTERNAL",
            true,
            new Provenance("SATELLITE_GOVERNED", sourceId, "2026-09-13T12:00:00Z", "SERVER_REGISTRY", "GOVERNED"),
            attributes);
    return new SatelliteInteractionRequest(
        "1.0",
        "msg-" + key,
        "11111111-1111-1111-1111-111111111111",
        "segsense",
        "EXPERIENCE",
        "REQUEST_DECISION",
        "2026-09-13T12:00:00Z",
        key,
        SatelliteContractV1.PURPOSE_INSURANCE,
        new Objective(objective, "USER_DECLARED", "2026-09-13T12:00:00Z"),
        new ContextBlock(null, snapshot),
        "INTERNAL",
        "SYNC",
        Map.of());
  }

  private static SatelliteInteractionRequest requestWithChannel(String channel, String key) {
    return requestWithChannel(channel, key, "UNDERSTAND_FAMILY_PROTECTION_OPTIONS");
  }

  private static SatelliteInteractionRequest requestWithChannel(String channel, String key, String objective) {
    return new SatelliteInteractionRequest(
        "1.0",
        "msg-" + key,
        "11111111-1111-1111-1111-111111111111",
        "segsense",
        "EXPERIENCE",
        "REQUEST_DECISION",
        "2026-09-13T12:00:00Z",
        key,
        SatelliteContractV1.PURPOSE_INSURANCE,
        new Objective(objective, "SATELLITE_GOVERNED", "2026-09-13T12:00:00Z"),
        governedContext(channel),
        "INTERNAL",
        "SYNC",
        Map.of());
  }

  private static SatelliteInteractionRequest requestWithProvenance(String sourceType, String key) {
    Map<String, String> attributes = new LinkedHashMap<>();
    attributes.put("channel", "SEGSENSE_PUBLIC_DEMO");
    ContextSnapshot snapshot =
        new ContextSnapshot(
            "1.0",
            "INTERNAL",
            true,
            new Provenance(sourceType, "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1", "2026-09-13T12:00:00Z", "SERVER_REGISTRY", "GOVERNED"),
            attributes);
    return new SatelliteInteractionRequest(
        "1.0",
        "msg-" + key,
        "11111111-1111-1111-1111-111111111111",
        "segsense",
        "EXPERIENCE",
        "REQUEST_DECISION",
        "2026-09-13T12:00:00Z",
        key,
        SatelliteContractV1.PURPOSE_INSURANCE,
        new Objective("UNDERSTAND_FAMILY_PROTECTION_OPTIONS", "SATELLITE_GOVERNED", "2026-09-13T12:00:00Z"),
        new ContextBlock(null, snapshot),
        "INTERNAL",
        "SYNC",
        Map.of());
  }

  private static ContextBlock governedContext(String channel) {
    Map<String, String> attributes = new LinkedHashMap<>();
    attributes.put("channel", channel);
    attributes.put("editorialPieceVersion", "demo-editorial-v1");
    attributes.put("purposeVersion", "demo-purpose-v1");
    return new ContextBlock(
        null,
        new ContextSnapshot(
            "1.0",
            "INTERNAL",
            true,
            new Provenance(
                "SATELLITE_GOVERNED",
                "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1",
                "2026-09-13T12:00:00Z",
                "SERVER_REGISTRY",
                "GOVERNED"),
            attributes));
  }

  public static SatelliteContractProperties properties() {
    SatelliteContractProperties properties = new SatelliteContractProperties();
    properties.setEnabled(true);
    SatelliteEntry segsense = new SatelliteEntry();
    segsense.setRole("EXPERIENCE");
    segsense.setSecret("test-only-secret");
    segsense.setCredentialAliases(List.of("local-demo-segsense"));
    segsense.setPurposes(List.of(SatelliteContractV1.PURPOSE_INSURANCE));
    segsense.setInteractionTypes(
        List.of("DECLARE_OBJECTIVE", "CONTINUE_CONTEXT", "REQUEST_DECISION", "QUERY_STATUS"));
    segsense.setClassifications(List.of("PUBLIC", "INTERNAL"));
    segsense.setGovernedContextIds(
        List.of(
            "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1",
            "SEGSENSE_INCOME_INTERRUPTION_SYNTHETIC_V1",
            "SEGSENSE_NEARBY_FIRES_SYNTHETIC_V1"));
    segsense.setDeclaredContextIds(
        List.of(
            "SEGSENSE_DECLARED_FAMILY_CONTINUITY_V1",
            "SEGSENSE_DECLARED_INCOME_INTERRUPTION_V1",
            "SEGSENSE_DECLARED_NEARBY_FIRES_V1",
            "SEGSENSE_DECLARED_HOME_PROTECTION_V1"));
    segsense.setAllowedObjectives(
        List.of(
            "UNDERSTAND_FAMILY_PROTECTION_OPTIONS",
            "UNDERSTAND_PROTECTION_OPTIONS",
            "COMPARE_COVERAGE_GAPS",
            "SIMULATE_HOME_QUOTE"));
    segsense.setAllowedAttributes(
        Map.of(
            "channel", List.of("SEGSENSE_PUBLIC_DEMO"),
            "constraint", List.of("no_quote", "unresolved_conflict", "missing_context", "editorial_not_risk"),
            "theme", List.of("family_continuity", "income_interruption", "nearby_fires", "home_protection"),
            "dwellingType", List.of("APARTMENT", "HOUSE"),
            "coverPeriodMonths", List.of("12"),
            "ratingRuleVersion", List.of("HOME_QUOTE_SYNTHETIC_V1")));
    properties.getRegistry().put("segsense", segsense);
    ProviderEntry provider = new ProviderEntry();
    provider.setRole("PROVIDER");
    provider.setStatus("TEST_DOUBLE");
    provider.setCapabilities(List.of(SatelliteContractV1.ILLUSTRATIVE_CAPABILITY, SatelliteContractV1.HOME_QUOTE_CAPABILITY));
    provider.setSecret("provider-test-only");
    properties.getProviders().put("insurance-provider-mock", provider);
    return properties;
  }
}
