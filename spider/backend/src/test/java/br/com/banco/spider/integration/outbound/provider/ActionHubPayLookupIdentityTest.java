package br.com.banco.spider.integration.outbound.provider;

import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionRequest;
import java.util.Map;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class ActionHubPayLookupIdentityTest {

  @Test
  void acceptsMatchingEnvelopeAndKeepsAmountAsDigits() {
    Map<String, Object> quote =
        ActionHubPayLookupIdentity.validatedQuote(
            request("pay-homolog-0001", "11111111-1111-4111-a111-111111111111"),
            completed("pay-homolog-0001", "11111111-1111-4111-a111-111111111111", "12550"));
    assertThat(quote.get("amountMinor")).isEqualTo("12550");
    assertThat(quote.get("origin")).isEqualTo("ACTIONHUB_PAY");
    assertThat(quote.get("automaticSettlement")).isEqualTo(false);
  }

  @Test
  void rejectsOtherReferenceOrCompany() {
    assertThat(
            ActionHubPayLookupIdentity.validatedQuote(
                request("pay-homolog-0001", "11111111-1111-4111-a111-111111111111"),
                completed("outra-ref", "11111111-1111-4111-a111-111111111111", "12550")))
        .isEmpty();
    assertThat(
            ActionHubPayLookupIdentity.validatedQuote(
                request("pay-homolog-0001", "11111111-1111-4111-a111-111111111111"),
                completed("pay-homolog-0001", "22222222-2222-4222-a222-222222222222", "12550")))
        .isEmpty();
  }

  @Test
  void rejectsFractionAndOversizedAmount() {
    assertThat(ActionHubPayLookupIdentity.amountDigits("12.5")).isNull();
    assertThat(ActionHubPayLookupIdentity.amountDigits("10000000000000000000")).isNull();
    assertThat(ActionHubPayLookupIdentity.amountDigits(12.55d)).isNull();
    assertThat(ActionHubPayLookupIdentity.amountDigits("12550")).isEqualTo("12550");
  }

  @Test
  void rejectsMismatchedCorrelation() {
    Map<String, Object> body = completed("pay-homolog-0001", "11111111-1111-4111-a111-111111111111", "12550");
    body.put("correlationId", "other-corr");
    assertThat(
            ActionHubPayLookupIdentity.validatedQuote(
                request("pay-homolog-0001", "11111111-1111-4111-a111-111111111111"), body))
        .isEmpty();
  }

  private static ExecutionRequest request(String reference, String companyId) {
    return new ExecutionRequest(
        "preq-1",
        "afc-1",
        "dec-1",
        "LOOKUP_ACTIONHUB_PAYMENT",
        "FINANCIAL_EXTERNAL_LOOKUP",
        null,
        "FINANCIAL",
        Map.of(),
        Map.of("externalReference", reference, "companyId", companyId, "payAppId", "homolog-padaria"));
  }

  private static Map<String, Object> completed(String reference, String companyId, String amount) {
    return new java.util.LinkedHashMap<>(
        Map.of(
            "status",
            "COMPLETED",
            "providerId",
            "actionhub-pay",
            "requestId",
            "preq-1",
            "correlationId",
            "afc-1",
            "capabilityId",
            "LOOKUP_ACTIONHUB_PAYMENT",
            "result",
            Map.of(
                "providerReference",
                reference,
                "companyId",
                companyId,
                "payAppId",
                "homolog-padaria",
                "externalStatus",
                "CONFIRMED",
                "amountMinor",
                amount,
                "currency",
                "BRL",
                "origin",
                "ACTIONHUB_PAY",
                "sandbox",
                true)));
  }
}
