package br.com.banco.spider.integration.inbound.http.contextuallink;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import br.com.banco.spider.contextuallink.application.PageAcquisitionPort;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.core.io.ClassPathResource;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.reactive.server.WebTestClient;
import reactor.core.publisher.Mono;

@SpringBootTest
@AutoConfigureWebTestClient(timeout = "PT30S")
@ActiveProfiles("local-demo")
class ContextualLinkGatewayHttpTest {

  @Autowired WebTestClient client;

  @MockBean PageAcquisitionPort pages;

  @Test
  void partnerPageIsStandaloneHtmlWithGenericLink() {
    String html =
        client
            .get()
            .uri("/demo/partner/agro-hoje")
            .exchange()
            .expectStatus()
            .isOk()
            .expectHeader()
            .contentTypeCompatibleWith("text/html")
            .expectBody(String.class)
            .returnResult()
            .getResponseBody();
    assertTrue(html.contains("CampoAberto"));
    assertTrue(html.contains("Quebra de safra aperta o caixa e obriga produtores a buscar recursos"));
    assertTrue(html.contains("Receita cai, mas o próximo ciclo não espera"));
    assertTrue(html.contains("Produtores tentam preservar capital de giro"));
    assertTrue(html.contains("Decisões precisam ser tomadas antes da nova safra"));
    assertTrue(html.contains("semente"));
    assertTrue(html.contains("fertilizante"));
    assertTrue(html.contains("SPIDERBANK"));
    assertTrue(html.contains("Conheça suas opções"));
    assertTrue(html.contains("href=\"http://127.0.0.1:8080/go\""));
    assertFalse(html.contains("href=\"http://127.0.0.1:8080/go?"));
    assertTrue(html.contains("target=\"_blank\""));
    assertTrue(html.contains("Provar link genérico"));
    assertTrue(html.contains("INEXISTENTE ANTES DO CLIQUE"));
    assertFalse(html.contains("intent="));
    assertFalse(html.contains("campaign="));
    assertFalse(html.contains("contextId="));
    assertFalse(html.contains("purpose="));
    assertFalse(html.contains("cropFailure="));
    assertFalse(html.contains("MOCK_ONLY"));
    assertTrue(html.contains("NENHUM"));
  }

  @Test
  void partnerHeroImageIsServed() {
    client
        .get()
        .uri("/demo/partner/hero.jpg")
        .exchange()
        .expectStatus()
        .isOk()
        .expectHeader()
        .contentTypeCompatibleWith("image/jpeg");
  }

  @Test
  void clickWithFullReferrerRedirectsToOpaqueContext() throws Exception {
    String article =
        new ClassPathResource("demo/partner/agro-hoje.html")
            .getContentAsString(StandardCharsets.UTF_8)
            .replace("{{GATEWAY_URL}}", "http://127.0.0.1:8080/go");
    when(pages.fetch(any()))
        .thenAnswer(
            invocation -> {
              URI uri = invocation.getArgument(0);
              return Mono.just(new PageAcquisitionPort.FetchedPage(uri, article));
            });

    client
        .get()
        .uri("/v1/demo/spiderbank/entry?ctx=ctx-before-click")
        .exchange()
        .expectStatus()
        .value(status -> assertTrue(status >= 400))
        .expectBody(String.class)
        .value(body -> assertTrue(body.contains("unknown context")));

    String location =
        client
            .get()
            .uri("/go")
            .header("Referer", "http://127.0.0.1:8080/demo/partner/agro-hoje")
            .exchange()
            .expectStatus()
            .isFound()
            .expectHeader()
            .valueMatches("Location", "^http://127\\.0\\.0\\.1:5180/spiderbank(?:/entry)?\\?ctx=ctx-.+")
            .returnResult(Void.class)
            .getResponseHeaders()
            .getFirst("Location");

    String ctx = location.substring(location.indexOf("ctx="));
    assertFalse(location.contains("intent"));
    assertFalse(location.contains("quebra"));
    assertFalse(location.contains("/console"));
    assertTrue(location.contains("/spiderbank?ctx="));

    client
        .get()
        .uri("/v1/demo/spiderbank/entry?" + ctx)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.click.clickId")
        .value(id -> assertTrue(id.toString().startsWith("clk-")))
        .jsonPath("$.click.contextId")
        .value(id -> assertTrue(id.toString().startsWith("ctx-")))
        .jsonPath("$.page.acquisitionStatus")
        .isEqualTo("CAPTURED")
        .jsonPath("$.page.sourceTitle")
        .value(
            title ->
                assertTrue(
                    title
                        .toString()
                        .contains(
                            "Quebra de safra aperta o caixa e obriga produtores a buscar recursos")))
        .jsonPath("$.page.safeExtractedText")
        .value(
            text -> {
              assertTrue(text.toString().contains("Receita cai, mas o próximo ciclo não espera"));
              assertTrue(text.toString().contains("capital de giro"));
            })
        .jsonPath("$.page.contentFingerprint")
        .value(fp -> assertTrue(fp.toString().startsWith("sha256:")))
        .jsonPath("$.partnerPublicName")
        .isEqualTo("CampoAberto")
        .jsonPath("$.boundaryFlags.intentCreated")
        .isEqualTo(false)
        .jsonPath("$.boundaryFlags.executionPlanCreated")
        .isEqualTo(false)
        .jsonPath("$.boundaryFlags.dataPlaneStarted")
        .isEqualTo(false)
        .jsonPath("$.intent")
        .doesNotExist()
        .jsonPath("$.executionPlan")
        .doesNotExist()
        .jsonPath("$.correlation.decisionId")
        .doesNotExist()
        .jsonPath("$.correlation.planId")
        .doesNotExist()
        .jsonPath("$.correlation.executionId")
        .doesNotExist();
  }

  @Test
  void extraQueryOnGoIsIgnoredAndNotCopiedToRedirect() {
    when(pages.fetch(any()))
        .thenReturn(
            Mono.just(
                new PageAcquisitionPort.FetchedPage(
                    URI.create("http://127.0.0.1:5180/partner/agro-hoje/"), "<html><title>x</title></html>")));
    client
        .get()
        .uri("/go?intent=workingCapital&campaign=safra")
        .header("Referer", "http://127.0.0.1:5180/partner/agro-hoje/")
        .exchange()
        .expectStatus()
        .isFound()
        .expectHeader()
        .value("Location", loc -> {
          assertFalse(loc.contains("intent"));
          assertFalse(loc.contains("campaign"));
          assertTrue(loc.contains("ctx=ctx-"));
        });
  }

  @Test
  void missingReferrerStillRedirectsWithMinimalContext() {
    String location =
        client
            .get()
            .uri("/go")
            .exchange()
            .expectStatus()
            .isFound()
            .returnResult(Void.class)
            .getResponseHeaders()
            .getFirst("Location");
    String ctx = location.substring(location.indexOf("ctx="));
    client
        .get()
        .uri("/v1/demo/spiderbank/entry?" + ctx)
        .exchange()
        .expectStatus()
        .isOk()
        .expectBody()
        .jsonPath("$.click.referrerAvailability")
        .isEqualTo("REFERRER_UNAVAILABLE")
        .jsonPath("$.page.acquisitionStatus")
        .isEqualTo("UNAVAILABLE")
        .jsonPath("$.page.sourceTitle")
        .isEqualTo("")
        .jsonPath("$.statusLabel")
        .value(label -> assertTrue(label.toString().contains("NÃO ADQUIRIDA")));
  }
}
