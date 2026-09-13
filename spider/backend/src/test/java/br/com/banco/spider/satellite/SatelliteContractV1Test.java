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
    verify(providers, never()).execute(any());
  }

  @Test
  void providerFailureIsDistinctStatus() {
    when(providers.execute(any())).thenReturn(Mono.just(ExecutionResult.unavailable()));
    var outcome = service.interact("segsense", request("UNDERSTAND_FAMILY_PROTECTION_OPTIONS", "idem-unavail")).block();
    assertEquals("PROVIDER_UNAVAILABLE", outcome.body().get("status"));
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

  private static SatelliteInteractionRequest request(String objective, String key) {
    return requestWithChannel("SEGSENSE_PUBLIC_DEMO", key, objective);
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
    segsense.setGovernedContextIds(List.of("SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1"));
    segsense.setAllowedObjectives(List.of("UNDERSTAND_FAMILY_PROTECTION_OPTIONS"));
    segsense.setAllowedAttributes(Map.of("channel", List.of("SEGSENSE_PUBLIC_DEMO")));
    properties.getRegistry().put("segsense", segsense);
    ProviderEntry provider = new ProviderEntry();
    provider.setRole("PROVIDER");
    provider.setStatus("TEST_DOUBLE");
    provider.setCapabilities(List.of(SatelliteContractV1.ILLUSTRATIVE_CAPABILITY));
    provider.setSecret("provider-test-only");
    properties.getProviders().put("insurance-provider-mock", provider);
    return properties;
  }
}
