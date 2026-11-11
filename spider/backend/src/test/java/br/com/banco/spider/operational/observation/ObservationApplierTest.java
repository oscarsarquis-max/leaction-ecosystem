package br.com.banco.spider.operational.observation;

import static org.junit.jupiter.api.Assertions.assertEquals;

import br.com.banco.spider.infrastructure.persistence.memory.InMemoryMonitorProjectionStore;
import br.com.banco.spider.operational.monitor.MonitorProjectionRecord;
import java.time.Instant;
import org.junit.jupiter.api.Test;

class ObservationApplierTest {

  @Test
  void projectsTheOriginalTimestampWithoutCallingTheMonitorInline() {
    InMemoryMonitorProjectionStore store = new InMemoryMonitorProjectionStore();
    Instant occurredAt = Instant.parse("2026-10-14T15:00:00Z");
    String payload =
        """
        {
          "kind": "TOUCH",
          "eventType": "SATELLITE_REQUEST_RECEIVED",
          "outcome": "INFO",
          "technicalState": "RECEIVED",
          "request": {
            "contractVersion": "1.4",
            "messageId": "afm-independence-1",
            "correlationId": "afc-independence-1",
            "satelliteId": "actionfinance",
            "satelliteRole": "EXPERIENCE",
            "interactionType": "QUERY_STATUS",
            "createdAt": "2026-10-14T15:00:00Z",
            "idempotencyKey": "list:test",
            "purpose": "FINANCIAL_EXTERNAL_LIST",
            "objective": {"text": "LIST_EXTERNAL_PAYMENTS", "origin": "SATELLITE_GOVERNED", "declaredAt": "2026-10-14T15:00:00Z"},
            "dataClassification": "INTERNAL",
            "responseChannel": "SYNC",
            "extensions": {"financialList": {"companyId": "624023a4-57e3-415c-b7d0-925ca1acd3b7", "environment": "PRODUCTION"}}
          }
        }
        """;

    new ObservationApplier().apply(store, occurredAt, payload);

    MonitorProjectionRecord record = store.findById("int:actionfinance:afm-independence-1").orElseThrow();
    assertEquals(occurredAt, record.createdAt());
    assertEquals("LIST_EXTERNAL_PAYMENTS", record.objective());
  }
}
