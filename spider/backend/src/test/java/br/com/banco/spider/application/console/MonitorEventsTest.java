package br.com.banco.spider.application.console;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import br.com.banco.spider.config.OperationalConsoleProperties;
import br.com.banco.spider.integration.inbound.http.console.OperationalConsoleHttpController;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryOperationalEventStore;
import br.com.banco.spider.operational.events.*;
import java.time.Instant;
import java.util.Map;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Mono;

class MonitorEventsTest {
  @Test void monitorOnlyAdvertisesScenariosWithPublishedRoutes() {
    var query = mock(OperationalConsoleQueryService.class, CALLS_REAL_METHODS);
    query.setOperationalEventStore(new InMemoryOperationalEventStore());
    var catalog = mock(br.com.banco.spider.execution.route.RouteCatalogPort.class);
    query.setMonitorRouteCatalog(catalog);
    when(catalog.findPublishedCandidates(anyString(), anyString(), anyString()))
        .thenReturn(Mono.just(java.util.List.of()));
    when(catalog.findPublishedCandidates("journey:mock", "mock", "RETRY_THEN_SUCCESS"))
        .thenReturn(Mono.just(java.util.List.of(mock(br.com.banco.spider.execution.route.RouteDefinition.class))));
    var result = query.monitorEvents().block();
    assertEquals(java.util.List.of("RETRY_THEN_SUCCESS"), result.get("availableScenarios"));
    assertEquals(false, result.get("truncated"));
  }

  @Test void simulationReadinessDoesNotInventACreditSatellite() {
    var query = mock(OperationalConsoleQueryService.class, CALLS_REAL_METHODS);
    var body = query.simulationReadiness().block();
    @SuppressWarnings("unchecked")
    var satellites = (java.util.List<java.util.Map<String, Object>>) body.get("satellites");
    var bank = satellites.stream().filter(item -> "spiderbank".equals(item.get("id"))).findFirst().orElseThrow();
    assertEquals(false, bank.get("available"));
    assertFalse(((java.util.List<?>) bank.get("missing")).isEmpty());
  }

  @Test void recentWindowReturnsNewestFirstAndEnforcesLimit() {
    var store = new InMemoryOperationalEventStore();
    var now = Instant.now();
    for (int i = 0; i < 3; i++) store.append(new OperationalEvent("ev-" + i, 1,
        OperationalEventType.SATELLITE_AUTHENTICATED, OperationalEventCategory.SECURITY,
        now.plusSeconds(i), "message-" + i, null, "correlation", "satellite-contract",
        OperationalEventOutcome.SUCCESS, null, Map.of("originSatellite", "segsense")));
    var found = store.findRecentBetween(now, now.plusSeconds(10), 2);
    assertEquals(2, found.size()); assertEquals("ev-2", found.get(0).eventId());
    assertEquals("ev-1", found.get(1).eventId());
  }

  @Test void attributesKeepOriginComponentExecutorButDropUnapprovedPayload() {
    var values = OperationalEventAttributes.builder().put("originSatellite", "segsense")
        .put("currentComponent", "SPIDER").put("executor", "insurance-provider-mock")
        .put("aiUsage", "NOT_USED").put("secret", "do-not-store").build().toMap();
    assertEquals("segsense", values.get("originSatellite"));
    assertEquals("SPIDER", values.get("currentComponent"));
    assertEquals("insurance-provider-mock", values.get("executor"));
    assertFalse(values.containsKey("secret"));
  }

  @Test void monitorRequiresAuthenticationAndOperationalEventAuthorization() {
    var auth = mock(OperationalConsoleAuthenticationPort.class);
    var authorization = mock(OperationalConsoleAuthorizationPort.class);
    var query = mock(OperationalConsoleQueryService.class);
    var props = new OperationalConsoleProperties(); props.setEnabled(true);
    var controller = new OperationalConsoleHttpController(auth, authorization, query, null, null, props, new MonitorCompanyAccess(props));
    when(auth.authenticate("missing")).thenReturn(Mono.just(OperationalConsoleSecurityContext.anonymous()));
    assertEquals(404, controller.monitorEvents("missing").block().getStatusCode().value());
    verifyNoInteractions(query, authorization);
    var identity = new OperationalConsoleSecurityContext("operator", "LOCAL", true);
    when(auth.authenticate("valid")).thenReturn(Mono.just(identity));
    when(authorization.authorize(identity, OperationalConsoleAction.VIEW_OPERATIONAL_EVENTS)).thenReturn(Mono.just(false));
    assertEquals(404, controller.monitorEvents("valid").block().getStatusCode().value());
    verifyNoInteractions(query);
    when(authorization.authorize(identity, OperationalConsoleAction.VIEW_OPERATIONAL_EVENTS)).thenReturn(Mono.just(true));
    when(query.monitorEvents()).thenReturn(Mono.just(Map.of("available",true,"items",java.util.List.of())));
    var response = controller.monitorEvents("valid").block();
    assertEquals(200,response.getStatusCode().value());
    assertTrue(response.getHeaders().getCacheControl().contains("no-store"));
  }

  @Test void companyScopeAllowsBoundExecutionAndHidesForeignId() {
    var auth = mock(OperationalConsoleAuthenticationPort.class);
    var authorization = mock(OperationalConsoleAuthorizationPort.class);
    var query = mock(OperationalConsoleQueryService.class);
    var props = new OperationalConsoleProperties();
    props.setEnabled(true);
    props.getCompanyScope().setEnabled(true);
    props.getCompanyScope().getBindings().put("owner:sandbox", "9c2e0a10-4f11-4b8a-9c2e-0a104f11000c");
    var controller = new OperationalConsoleHttpController(auth, authorization, query, null, null, props, new MonitorCompanyAccess(props));
    var identity = new OperationalConsoleSecurityContext("owner:sandbox", "SANDBOX", true);
    when(auth.authenticate("sandbox-operator")).thenReturn(Mono.just(identity));
    when(authorization.authorize(identity, OperationalConsoleAction.VIEW_OPERATIONAL_EVENTS)).thenReturn(Mono.just(true));
    var owned = new br.com.banco.spider.operational.readmodel.OperationalEventView(
        "ev-ok", 1, OperationalEventType.SATELLITE_COMPANY_AUTHORIZED, OperationalEventCategory.SECURITY,
        Instant.parse("2026-10-01T12:00:00Z"), "afm-ok", null, "corr-ok", "satellite-contract",
        OperationalEventOutcome.SUCCESS, null, Map.of("companyId", "9c2e0a10-4f11-4b8a-9c2e-0a104f11000c"));
    var foreign = new br.com.banco.spider.operational.readmodel.OperationalEventView(
        "ev-no", 1, OperationalEventType.SATELLITE_COMPANY_AUTHORIZED, OperationalEventCategory.SECURITY,
        Instant.parse("2026-10-01T12:00:01Z"), "afm-no", null, "corr-no", "satellite-contract",
        OperationalEventOutcome.SUCCESS, null, Map.of("companyId", "624023a4-57e3-415c-b7d0-925ca1acd3b7"));
    when(query.listOperationalEvents("afm-ok")).thenReturn(Mono.just(java.util.List.of(owned)));
    when(query.listOperationalEvents("afm-no")).thenReturn(Mono.just(java.util.List.of(foreign)));
    assertEquals(200, controller.operationalEvents("afm-ok", "sandbox-operator").block().getStatusCode().value());
    assertEquals(404, controller.operationalEvents("afm-no", "sandbox-operator").block().getStatusCode().value());
  }
}
