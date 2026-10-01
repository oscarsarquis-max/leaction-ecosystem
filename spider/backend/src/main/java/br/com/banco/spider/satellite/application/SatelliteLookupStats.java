package br.com.banco.spider.satellite.application;

import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicInteger;

public final class SatelliteLookupStats {

  private static final AtomicInteger DISPATCHED = new AtomicInteger();
  private static final AtomicInteger LIST_DISPATCHED = new AtomicInteger();
  private static final ConcurrentLinkedQueue<String> CORRELATIONS = new ConcurrentLinkedQueue<>();
  private static final ConcurrentLinkedQueue<String> LIST_CORRELATIONS = new ConcurrentLinkedQueue<>();

  private SatelliteLookupStats() {}

  public static void recordDispatch(String capabilityId, String correlationId) {
    if (SatelliteContractV1.LIST_PAYMENT_TRANSACTIONS.equals(capabilityId)) {
      LIST_DISPATCHED.incrementAndGet();
      if (correlationId != null && !correlationId.isBlank()) {
        LIST_CORRELATIONS.add(correlationId);
      }
      return;
    }
    if (!SatelliteContractV1.LOOKUP_ACTIONHUB_PAYMENT.equals(capabilityId)) {
      return;
    }
    DISPATCHED.incrementAndGet();
    if (correlationId != null && !correlationId.isBlank()) {
      CORRELATIONS.add(correlationId);
    }
  }

  public static Map<String, Object> snapshot() {
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("capabilityId", SatelliteContractV1.LOOKUP_ACTIONHUB_PAYMENT);
    body.put("dispatched", DISPATCHED.get());
    List<String> recent = new ArrayList<>(CORRELATIONS);
    body.put("correlations", recent.subList(Math.max(0, recent.size() - 20), recent.size()));
    body.put("listCapabilityId", SatelliteContractV1.LIST_PAYMENT_TRANSACTIONS);
    body.put("listDispatched", LIST_DISPATCHED.get());
    List<String> listRecent = new ArrayList<>(LIST_CORRELATIONS);
    body.put("listCorrelations", listRecent.subList(Math.max(0, listRecent.size() - 20), listRecent.size()));
    return body;
  }
}
