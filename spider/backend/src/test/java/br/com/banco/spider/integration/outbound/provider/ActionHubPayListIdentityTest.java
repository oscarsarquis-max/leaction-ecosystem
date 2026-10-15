package br.com.banco.spider.integration.outbound.provider;

import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionRequest;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
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
}
