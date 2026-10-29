package br.com.banco.spider.satellite.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.satellite.application.ActionHubBibliotecaCallbackContract.Decision;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ActionHubBibliotecaCallbackContractTest {

  @Test
  void validEventResumesOnceAndDuplicatesDoNot() {
    var store = new ActionHubBibliotecaCallbackContract.Store();
    Map<String, Object> first = event("cb-loja-1", "2026-10-08T22:00:00Z", "pending", "pending");
    var accepted = store.accept(first);
    assertEquals(Decision.ACCEPT, accepted.decision());
    assertTrue(accepted.resume());
    var duplicate = store.accept(first);
    assertEquals(Decision.DUPLICATE, duplicate.decision());
    assertFalse(duplicate.resume());
    Map<String, Object> sameTransition =
        event("cb-loja-2", "2026-10-08T22:01:00Z", "pending", "pending");
    var again = store.accept(sameTransition);
    assertEquals(Decision.ACCEPT, again.decision());
    assertFalse(again.resume());
  }

  @Test
  void outOfOrderAndInvalidAreRejectedWithoutResume() {
    var store = new ActionHubBibliotecaCallbackContract.Store();
    assertEquals(
        Decision.ACCEPT,
        store.accept(event("cb-later", "2026-10-08T22:10:00Z", "authorized", "pending")).decision());
    var late = store.accept(event("cb-early", "2026-10-08T22:00:00Z", "pending", "pending"));
    assertEquals(Decision.OUT_OF_ORDER, late.decision());
    assertFalse(late.resume());
    Map<String, Object> bad = event("cb-bad", "2026-10-08T22:20:00Z", "authorized", "confirmed");
    bad.put("cardNumber", "411111");
    assertEquals(Decision.INVALID, ActionHubBibliotecaCallbackContract.validate(bad).decision());
    Map<String, Object> foreign = event("cb-pay", "2026-10-08T22:21:00Z", "authorized", "confirmed");
    foreign.put("capabilityId", SatelliteContractV1.LOOKUP_ACTIONHUB_PAYMENT);
    assertEquals(Decision.INVALID, ActionHubBibliotecaCallbackContract.validate(foreign).decision());
  }

  private static Map<String, Object> event(
      String id, String occurredAt, String commercial, String financial) {
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("contractVersion", "1.5");
    body.put("eventType", ActionHubBibliotecaCallbackContract.EVENT_TYPE);
    body.put("callbackEventId", id);
    body.put("correlationId", "loja-corr-callback-0001");
    body.put("occurredAt", occurredAt);
    body.put("providerId", "actionhub-biblioteca");
    body.put("capabilityId", SatelliteContractV1.START_HUB_CATALOG_CHECKOUT);
    body.put("commercialStatus", commercial);
    body.put("financialStatus", financial);
    return body;
  }
}
