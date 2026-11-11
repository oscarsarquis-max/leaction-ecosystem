package br.com.actionfinance.infrastructure.integration;

import br.com.actionfinance.configuration.ActionFinanceProperties;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

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

    @Test
    @SuppressWarnings("unchecked")
    void listSends16AndRejectsAnotherContractWithoutLoggingPayer() throws Exception {
        String secretName = "Pagador Exemplo";
        String secretEmail = "pagador.exemplo@exemplo.test";
        ObjectMapper mapper = new ObjectMapper();
        List<String> requests = new ArrayList<>();
        AtomicInteger calls = new AtomicInteger();
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext(
                "/v1/satellites/interactions",
                exchange -> {
                    requests.add(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
                    int n = calls.incrementAndGet();
                    String contract = n == 2 ? "1.4" : "1.3";
                    if (n == 1) {
                        contract = "1.6";
                    }
                    byte[] body =
                            mapper.writeValueAsBytes(
                                    Map.of(
                                            "status",
                                            "READY",
                                            "contractVersion",
                                            contract,
                                            "correlationId",
                                            "corr-spider",
                                            "resultSummary",
                                            Map.of(
                                                    "items",
                                                    List.of(
                                                            Map.of(
                                                                    "transactionId",
                                                                    "tx-1",
                                                                    "payerName",
                                                                    secretName,
                                                                    "payerEmail",
                                                                    secretEmail)),
                                                    "itemCount",
                                                    1)));
                    exchange.getResponseHeaders().set("Content-Type", "application/json");
                    exchange.sendResponseHeaders(200, body.length);
                    exchange.getResponseBody().write(body);
                    exchange.close();
                });
        server.start();
        Logger logger = (Logger) LoggerFactory.getLogger(HttpSpiderInteractionClient.class);
        ListAppender<ILoggingEvent> appender = new ListAppender<>();
        appender.start();
        logger.addAppender(appender);
        try {
            ActionFinanceProperties properties = new ActionFinanceProperties();
            properties.getIntegration().setSpiderBaseUrl("http://127.0.0.1:" + server.getAddress().getPort());
            properties.getIntegration().setSpiderSecret("segredo-de-teste");
            properties.getIntegration().setSatelliteId("actionfinance");
            HttpSpiderInteractionClient client = new HttpSpiderInteractionClient(properties);
            var accepted =
                    client.list(
                            "corr-list-16aa",
                            "list-16aa",
                            "11111111-1111-4111-8111-111111111111",
                            "HOMOLOG",
                            null,
                            5);
            assertTrue(accepted.available());
            assertEquals(secretName, accepted.items().getFirst().get("payerName"));
            var rejected =
                    client.list(
                            "corr-list-16bb",
                            "list-16bb",
                            "11111111-1111-4111-8111-111111111111",
                            "HOMOLOG",
                            null,
                            5);
            assertFalse(rejected.available());
            assertTrue(rejected.items().isEmpty());
            client.lookup("corr-lookup-13", "lookup-13", "11111111-1111-4111-8111-111111111111", null, "ref-1");
        } finally {
            logger.detachAppender(appender);
            server.stop(0);
        }
        Map<String, Object> listed = mapper.readValue(requests.get(0), Map.class);
        Map<String, Object> listedAgain = mapper.readValue(requests.get(1), Map.class);
        Map<String, Object> lookedUp = mapper.readValue(requests.get(2), Map.class);
        assertEquals("1.6", listed.get("contractVersion"));
        assertEquals("1.6", snapshotVersion(listed));
        assertEquals("1.6", listedAgain.get("contractVersion"));
        assertEquals("1.6", snapshotVersion(listedAgain));
        assertEquals("1.3", lookedUp.get("contractVersion"));
        assertEquals("1.3", snapshotVersion(lookedUp));
        String logs = appender.list.stream().map(ILoggingEvent::getFormattedMessage).reduce("", String::concat);
        assertFalse(logs.contains(secretName));
        assertFalse(logs.contains(secretEmail));
    }

    @SuppressWarnings("unchecked")
    private static String snapshotVersion(Map<String, Object> body) {
        Map<String, Object> context = (Map<String, Object>) body.get("context");
        Map<String, Object> snapshot = (Map<String, Object>) context.get("snapshot");
        return (String) snapshot.get("schemaVersion");
    }
}
