package br.com.actionfinance.infrastructure.integration;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class HttpSpiderInteractionClientTest {

    @Test
    void distinguishesRejectedFromUnavailableWithoutInventingReady() {
        assertEquals("SPIDER_REJECTED", HttpSpiderInteractionClient.listFailureCode("REJECTED"));
        assertEquals("SPIDER_UNAVAILABLE", HttpSpiderInteractionClient.listFailureCode("PROVIDER_UNAVAILABLE"));
        assertEquals(
                "A Spider recusou a listagem.",
                HttpSpiderInteractionClient.listFailureMessage("REJECTED", null));
        assertEquals(
                "A Spider validou o satélite, mas o executor da capability não respondeu.",
                HttpSpiderInteractionClient.listFailureMessage(
                        "PROVIDER_UNAVAILABLE",
                        "A Spider validou o satélite, mas o executor da capability não respondeu."));
        assertEquals(
                "A Spider não devolveu a listagem.",
                HttpSpiderInteractionClient.listFailureMessage("PROVIDER_UNAVAILABLE", null));
        assertEquals(
                "A Spider recusou o pedido. Referência de suporte: afp-3843271c-1",
                HttpSpiderInteractionClient.transportFailureMessage("INVALID_PAYLOAD", "afp-3843271c-1"));
        assertEquals(
                "Não foi possível consultar a Spider. Os itens já importados foram preservados. Ref. afp-1",
                HttpSpiderInteractionClient.transportFailureMessage(null, "afp-1"));
        assertEquals(
                "CONTRACT",
                HttpSpiderInteractionClient.diagnoseFailureClass(
                        "INVALID_PAYLOAD",
                        new org.springframework.web.client.HttpClientErrorException(
                                org.springframework.http.HttpStatus.BAD_REQUEST)));
        assertEquals(
                "PROVIDER",
                HttpSpiderInteractionClient.diagnoseFailureClass(
                        "PROVIDER_UNAVAILABLE",
                        new org.springframework.web.client.HttpServerErrorException(
                                org.springframework.http.HttpStatus.BAD_GATEWAY)));
        assertEquals("TRANSPORT", HttpSpiderInteractionClient.diagnoseFailureClass(null, null));
    }

    @Test
    @SuppressWarnings("unchecked")
    void publishedListContractFixtureMatchesClientEnvelope() throws Exception {
        Map<String, Object> fixture;
        try (var in = getClass().getClassLoader().getResourceAsStream(
                "contracts/actionfinance-list-external-payments-1.4.valid.json")) {
            fixture = new com.fasterxml.jackson.databind.ObjectMapper().readValue(in, Map.class);
        }
        Map<String, Object> invalid;
        try (var in = getClass().getClassLoader().getResourceAsStream(
                "contracts/actionfinance-list-external-payments-1.4.invalid-company.json")) {
            invalid = new com.fasterxml.jackson.databind.ObjectMapper().readValue(in, Map.class);
        }
        assertEquals("1.4", fixture.get("contractVersion"));
        assertEquals("FINANCIAL_EXTERNAL_LIST", fixture.get("purpose"));
        assertEquals("LIST_EXTERNAL_PAYMENTS", ((Map<String, Object>) fixture.get("objective")).get("text"));
        Map<String, Object> list = (Map<String, Object>) ((Map<String, Object>) fixture.get("extensions")).get("financialList");
        assertEquals("ACTIONHUB_PAY", list.get("originSystem"));
        assertEquals("9c2e0a10-4f11-4b8a-9c2e-0a104f11000c", list.get("companyId"));
        assertEquals("HOMOLOG", list.get("environment"));
        Map<String, Object> invalidList =
                (Map<String, Object>) ((Map<String, Object>) invalid.get("extensions")).get("financialList");
        assertEquals("624023a4-57e3-415c-b7d0-925ca1acd3b7", invalidList.get("companyId"));
        assertEquals("PRODUCTION", invalidList.get("environment"));
    }

    @Test
    void productionCompanyIsNotSentToTheSandboxSpider() {
        assertEquals(
                true,
                HttpSpiderInteractionClient.productionTargetsSandbox(
                        "PRODUCTION", "https://sandbox-api.spider.actionhub.com.br"));
        assertEquals(
                false,
                HttpSpiderInteractionClient.productionTargetsSandbox(
                        "PRODUCTION", "https://api.spider.actionhub.com.br"));
        assertEquals(
                false,
                HttpSpiderInteractionClient.productionTargetsSandbox(
                        "HOMOLOG", "https://sandbox-api.spider.actionhub.com.br"));
    }
}
