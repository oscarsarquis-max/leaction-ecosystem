package br.com.banco.spider.integration.outbound.provider;

import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionRequest;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ActionHubPayListIdentityTest {

  @Test
  void keepsMissingAmountAndRejectsForeignCompany() {
    ExecutionRequest request =
        new ExecutionRequest(
            "preq-1",
            "corr-1",
            "spd-1",
            SatelliteContractV1.LIST_PAYMENT_TRANSACTIONS,
            SatelliteContractV1.PURPOSE_FINANCIAL_EXTERNAL_LIST,
            "company",
            "INTERNAL",
            Map.of(),
            Map.of(
                "companyId",
                "11111111-1111-4111-a111-111111111111",
                "payAppId",
                "homolog-padaria",
                "environment",
                "HOMOLOG"));
    Map<String, Object> ok =
        ActionHubPayListIdentity.validatedQuote(
            request,
            Map.of(
                "status",
                "COMPLETED",
                "providerId",
                "actionhub-pay",
                "requestId",
                "preq-1",
                "correlationId",
                "corr-1",
                "capabilityId",
                "LIST_PAYMENT_TRANSACTIONS",
                "result",
                Map.of(
                    "companyId",
                    "11111111-1111-4111-a111-111111111111",
                    "payAppId",
                    "homolog-padaria",
                    "environment",
                    "HOMOLOG",
                    "origin",
                    "ACTIONHUB_PAY",
                    "testLabeled",
                    true,
                    "nextCursor",
                    "cursor-1",
                    "items",
                    List.of(
                        Map.of(
                            "transactionId",
                            "tx-1",
                            "amountMinor",
                            "12550",
                            "currency",
                            "BRL",
                            "normalizedStatus",
                            "CONFIRMED"),
                        Map.of(
                            "transactionId",
                            "tx-2",
                            "amountAbsent",
                            true,
                            "normalizedStatus",
                            "CONFIRMED"),
                        Map.of(
                            "transactionId",
                            "tx-absent",
                            "amountMinor",
                            "9000",
                            "paidAmountAbsent",
                            true,
                            "cardToken",
                            "should-drop",
                            "normalizedStatus",
                            "CONFIRMED")))));
    assertEquals(3, ok.get("itemCount"));
    assertEquals(false, ok.get("importPersisted"));
    @SuppressWarnings("unchecked")
    List<Map<String, Object>> plain = (List<Map<String, Object>>) ok.get("items");
    assertEquals("12550", plain.getFirst().get("amountMinor"));
    assertEquals(false, plain.getFirst().containsKey("paidAmountAbsent"));
    assertEquals(false, plain.getFirst().containsKey("payerLabel"));
    assertEquals(false, plain.get(2).containsKey("paidAmountAbsent"));
    assertEquals(false, plain.get(2).containsKey("cardToken"));
    assertEquals("9000", plain.get(2).get("amountMinor"));
    Map<String, Object> withPayer =
        ActionHubPayListIdentity.validatedQuote(
            request,
            Map.of(
                "status",
                "COMPLETED",
                "providerId",
                "actionhub-pay",
                "requestId",
                "preq-1",
                "correlationId",
                "corr-1",
                "capabilityId",
                "LIST_PAYMENT_TRANSACTIONS",
                "result",
                Map.of(
                    "companyId",
                    "11111111-1111-4111-a111-111111111111",
                    "payAppId",
                    "homolog-padaria",
                    "environment",
                    "HOMOLOG",
                    "items",
                    List.of(
                        Map.ofEntries(
                            Map.entry("transactionId", "11111111-2222-4333-8444-555555555555"),
                            Map.entry("amountMinor", "9000"),
                            Map.entry("paidAmountMinor", "9000"),
                            Map.entry("paidAmountAbsent", false),
                            Map.entry("normalizedStatus", "CONFIRMED"),
                            Map.entry("paymentMethod", "pix"),
                            Map.entry("payerKind", "EMAIL"),
                            Map.entry("payerLabel", "cliente@exemplo.test"),
                            Map.entry("payerProvenance", "ACTIONHUB_PAY"),
                            Map.entry("commercialApplication", "lojadepaes"),
                            Map.entry("commercialDescription", "Consulta avulsa"),
                            Map.entry("processorName", "Mercado Pago"),
                            Map.entry("providerStatus", "approved"))))));
    @SuppressWarnings("unchecked")
    List<Map<String, Object>> kept = (List<Map<String, Object>>) withPayer.get("items");
    assertEquals("9000", kept.getFirst().get("paidAmountMinor"));
    assertEquals("cliente@exemplo.test", kept.getFirst().get("payerLabel"));
    assertEquals("pix", kept.getFirst().get("paymentMethod"));
    assertEquals("lojadepaes", kept.getFirst().get("commercialApplication"));
    Map<String, Object> foreign =
        ActionHubPayListIdentity.validatedQuote(
            request,
            Map.of(
                "status",
                "COMPLETED",
                "providerId",
                "actionhub-pay",
                "capabilityId",
                "LIST_PAYMENT_TRANSACTIONS",
                "result",
                Map.of(
                    "companyId",
                    "22222222-2222-4222-a222-222222222222",
                    "items",
                    List.of())));
    assertTrue(foreign.isEmpty());
  }

  private static final String PRE_CHANGE_ITEMS =
      "[{\"transactionId\":\"tx-snap\",\"orderReference\":\"hub-snap\",\"processorReference\":null,\"companyBinding\":null,\"origin\":\"ACTIONHUB_PAY\",\"environment\":null,\"originalStatus\":null,\"normalizedStatus\":\"CONFIRMED\",\"amountMinor\":\"100\",\"amountAbsent\":false,\"currency\":null,\"createdAt\":null,\"updatedAt\":null,\"originRevision\":null,\"testLabeled\":false,\"reviewRequired\":false,\"payerKind\":\"EMAIL\",\"payerLabel\":\"cliente@exemplo.test\"}]";

  @Test
  void contract14KeepsTheListShapeFromBeforeExplicitPayer() throws Exception {
    Map<String, Object> quote = ActionHubPayListIdentity.validatedQuote(snapshotRequest(Map.of()), snapshotBody());
    assertEquals(PRE_CHANGE_ITEMS, new ObjectMapper().writeValueAsString(quote.get("items")));
  }

  @Test
  void contract16CopiesExplicitFieldsWithoutRewritingThem() {
    Map<String, Object> quote =
        ActionHubPayListIdentity.validatedQuote(
            snapshotRequest(Map.of("satelliteContractVersion", "1.6")), snapshotBody());
    @SuppressWarnings("unchecked")
    Map<String, Object> item = ((List<Map<String, Object>>) quote.get("items")).getFirst();
    assertEquals("Cliente Exemplo", item.get("payerName"));
    assertEquals("cliente@exemplo.test", item.get("payerEmail"));
    assertEquals("PED-1", item.get("storeOrderReference"));
    assertEquals("req-1", item.get("storePaymentRequestId"));
    assertEquals("mp-1", item.get("processorPaymentId"));
    assertEquals("2026-10-27T15:04:00.000Z", item.get("processorApprovedAt"));
    assertEquals(2, item.get("processorInstallments"));
    assertEquals("Checkout avulso", item.get("purchaseDescription"));
    assertEquals("cliente@exemplo.test", item.get("payerLabel"));
    Map<String, Object> sparse = new LinkedHashMap<>();
    sparse.put("transactionId", "tx-null");
    sparse.put("amountMinor", "100");
    sparse.put("normalizedStatus", "CONFIRMED");
    sparse.put("payerLabel", "cliente@exemplo.test");
    sparse.put("payerName", null);
    sparse.put("payerEmail", null);
    Map<String, Object> absent =
        ActionHubPayListIdentity.validatedQuote(
            snapshotRequest(Map.of("satelliteContractVersion", "1.6")),
            snapshotBody(List.of(sparse)));
    @SuppressWarnings("unchecked")
    Map<String, Object> copied = ((List<Map<String, Object>>) absent.get("items")).getFirst();
    for (String key : List.of(
        "payerName",
        "payerEmail",
        "storeOrderReference",
        "storePaymentRequestId",
        "processorPaymentId",
        "processorApprovedAt",
        "processorInstallments",
        "purchaseDescription")) {
      assertTrue(copied.containsKey(key));
      assertEquals(null, copied.get(key));
      assertNotEquals("", copied.get(key));
    }
    assertEquals("cliente@exemplo.test", copied.get("payerLabel"));
    for (String invented : List.of(
        "feeDetails", "netReceivedAmount", "moneyReleaseDate", "payerDocument", "lineItems")) {
      assertEquals(false, copied.containsKey(invented));
    }
  }

  private static ExecutionRequest snapshotRequest(Map<String, String> quoteInputs) {
    return new ExecutionRequest(
        "preq-snap",
        "corr-snap",
        "spd-snap",
        SatelliteContractV1.LIST_PAYMENT_TRANSACTIONS,
        SatelliteContractV1.PURPOSE_FINANCIAL_EXTERNAL_LIST,
        "company",
        "INTERNAL",
        quoteInputs,
        Map.of(
            "companyId", "11111111-1111-4111-a111-111111111111",
            "payAppId", "homolog-padaria",
            "environment", "HOMOLOG"));
  }

  private static Map<String, Object> snapshotBody() {
    Map<String, Object> item = new LinkedHashMap<>();
    item.put("transactionId", "tx-snap");
    item.put("orderReference", "hub-snap");
    item.put("amountMinor", "100");
    item.put("normalizedStatus", "CONFIRMED");
    item.put("payerKind", "EMAIL");
    item.put("payerLabel", "cliente@exemplo.test");
    item.put("payerName", "Cliente Exemplo");
    item.put("payerEmail", "cliente@exemplo.test");
    item.put("storeOrderReference", "PED-1");
    item.put("storePaymentRequestId", "req-1");
    item.put("processorPaymentId", "mp-1");
    item.put("processorApprovedAt", "2026-10-27T15:04:00.000Z");
    item.put("processorInstallments", 2);
    item.put("purchaseDescription", "Checkout avulso");
    return snapshotBody(List.of(item));
  }

  private static Map<String, Object> snapshotBody(List<Map<String, Object>> items) {
    return Map.of(
        "status", "COMPLETED",
        "providerId", "actionhub-pay",
        "requestId", "preq-snap",
        "correlationId", "corr-snap",
        "capabilityId", "LIST_PAYMENT_TRANSACTIONS",
        "result",
        Map.of(
            "companyId", "11111111-1111-4111-a111-111111111111",
            "payAppId", "homolog-padaria",
            "environment", "HOMOLOG",
            "items", items));
  }
}
