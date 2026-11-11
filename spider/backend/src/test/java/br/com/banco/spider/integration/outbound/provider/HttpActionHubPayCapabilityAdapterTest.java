package br.com.banco.spider.integration.outbound.provider;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.config.SatelliteContractProperties;
import br.com.banco.spider.config.SatelliteContractProperties.ProviderEntry;
import br.com.banco.spider.satellite.application.SatelliteRegistry;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionRequest;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.client.ClientResponse;
import org.springframework.web.reactive.function.client.WebClient;

class HttpActionHubPayCapabilityAdapterTest {

  @Test
  void listPaymentTransactionsIsNeverSentAsContract13() {
    assertEquals("1.4", HttpActionHubPayCapabilityAdapter.outboundContractVersion(
        SatelliteContractV1.LIST_PAYMENT_TRANSACTIONS));
    assertNotEquals(
        "1.3",
        HttpActionHubPayCapabilityAdapter.outboundPayload(listRequest()).get("contractVersion"));
    assertEquals(
        "1.3",
        HttpActionHubPayCapabilityAdapter.outboundContractVersion(SatelliteContractV1.LOOKUP_ACTIONHUB_PAYMENT));
  }

  @Test
  void returnedContractMustMatchTheVersionSentToPay() {
    HttpActionHubPayCapabilityAdapter adapter = adapter();
    ExecutionResult matched = adapter.execute(listRequest()).block();
    assertTrue(matched.available());
    ExecutionResult mismatched =
        new HttpActionHubPayCapabilityAdapter(responding("1.5"), registry()).execute(listRequest()).block();
    assertFalse(mismatched.available());
  }

  private static HttpActionHubPayCapabilityAdapter adapter() {
    return new HttpActionHubPayCapabilityAdapter(responding("1.4"), registry());
  }

  private static WebClient.Builder responding(String contractVersion) {
    String body =
        """
        {"status":"COMPLETED","providerId":"actionhub-pay","contractVersion":"%s","requestId":"preq","correlationId":"corr","capabilityId":"LIST_PAYMENT_TRANSACTIONS","result":{"companyId":"co","payAppId":"app","environment":"HOMOLOG","items":[{"transactionId":"tx","amountMinor":"100","normalizedStatus":"CONFIRMED"}]}}
        """
            .formatted(contractVersion);
    return WebClient.builder()
        .exchangeFunction(
            request ->
                reactor.core.publisher.Mono.just(
                    ClientResponse.create(HttpStatus.OK)
                        .header("Content-Type", MediaType.APPLICATION_JSON_VALUE)
                        .body(body)
                        .build()));
  }

  private static SatelliteRegistry registry() {
    SatelliteContractProperties properties = new SatelliteContractProperties();
    ProviderEntry provider = new ProviderEntry();
    provider.setRole("PROVIDER");
    provider.setStatus("ACTIVE");
    provider.setBaseUrl("http://pay.invalid");
    provider.setSecret("test-only");
    provider.setTimeout(Duration.ofSeconds(2));
    provider.setCapabilities(
        List.of(
            SatelliteContractV1.LIST_PAYMENT_TRANSACTIONS,
            SatelliteContractV1.LOOKUP_ACTIONHUB_PAYMENT));
    properties.getProviders().put("actionhub-pay", provider);
    return new SatelliteRegistry(properties);
  }

  private static ExecutionRequest listRequest() {
    return new ExecutionRequest(
        "preq",
        "corr",
        "spd",
        SatelliteContractV1.LIST_PAYMENT_TRANSACTIONS,
        SatelliteContractV1.PURPOSE_FINANCIAL_EXTERNAL_LIST,
        "company",
        "INTERNAL",
        Map.of(),
        Map.of("companyId", "co", "payAppId", "app", "environment", "HOMOLOG"));
  }
}
