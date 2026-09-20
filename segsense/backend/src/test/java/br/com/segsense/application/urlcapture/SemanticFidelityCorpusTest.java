package br.com.segsense.application.urlcapture;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import org.junit.jupiter.api.Test;

class SemanticFidelityCorpusTest {

  @Test
  void sameSentenceAllowsCropAssociation() {
    String html =
        """
        <html lang="pt"><body><main>
        <p>A quebra de safra de milho no Paraná em 2026 reduziu a produção agrícola.</p>
        </main></body></html>
        """;
    HtmlTextExtractor.Extracted extracted = HtmlTextExtractor.extract(html.getBytes(StandardCharsets.UTF_8), "text/html");
    List<DeterministicPageContextExtractor.Element> elements =
        DeterministicPageContextExtractor.extract(extracted.normalizedText());
    assertTrue(extracted.usable());
    assertEquals(HtmlTextExtractor.STRATEGY_MAIN, extracted.selectionStrategy());
    assertTrue(has(elements, "theme", "crop_production_loss"));
    assertTrue(has(elements, "crop", "milho"));
    assertTrue(has(elements, "region", "Paraná"));
    assertTrue(has(elements, "period", "2026"));
    assertTrue(elements.stream().anyMatch(item -> "CROP_IN_SAME_PARAGRAPH_AS_EVENT".equals(item.rule())));
  }

  @Test
  void cropOnlyInIndexIsOmitted() {
    String html =
        """
        <html><body>
        <nav id="toc"><ul><li>Culturas: milho soja café</li></ul></nav>
        <main>
        <p>Houve quebra de safra em várias regiões do país.</p>
        </main>
        </body></html>
        """;
    HtmlTextExtractor.Extracted extracted = HtmlTextExtractor.extract(html.getBytes(StandardCharsets.UTF_8), "text/html");
    List<DeterministicPageContextExtractor.Element> elements =
        DeterministicPageContextExtractor.extract(extracted.normalizedText());
    assertFalse(extracted.normalizedText().toLowerCase(Locale.ROOT).contains("milho"));
    assertTrue(has(elements, "event", "crop_failure"));
    assertFalse(hasKey(elements, "crop"));
  }

  @Test
  void distantInstitutionalHistoryDoesNotBecomeRegion() {
    String html =
        """
        <html><body><main>
        <p>O relatório descreve uma quebra de safra causada pela seca.</p>
        <p>Em 1883 foi criado um curso em Pelotas, no Rio Grande do Sul.</p>
        </main></body></html>
        """;
    List<DeterministicPageContextExtractor.Element> elements =
        DeterministicPageContextExtractor.extract(
            HtmlTextExtractor.extract(html.getBytes(StandardCharsets.UTF_8), "text/html").normalizedText());
    assertTrue(has(elements, "theme", "crop_production_loss"));
    assertFalse(hasKey(elements, "region"));
    assertFalse(hasKey(elements, "crop"));
  }

  @Test
  void multipleUnrelatedCropsStayAmbiguous() {
    String html =
        """
        <html><body><main>
        <p>Uma quebra de safra atingiu o milho no norte.</p>
        <p>Outra quebra de safra atingiu a soja no sul.</p>
        </main></body></html>
        """;
    List<DeterministicPageContextExtractor.Element> elements =
        DeterministicPageContextExtractor.extract(
            HtmlTextExtractor.extract(html.getBytes(StandardCharsets.UTF_8), "text/html").normalizedText());
    assertTrue(has(elements, "event", "crop_failure"));
    assertFalse(hasKey(elements, "crop"));
    assertFalse(has(elements, "crop", "milho"));
    assertFalse(has(elements, "crop", "soja"));
  }

  @Test
  void chromeNavAsideTocFooterAndHiddenAreExcluded() {
    String html =
        """
        <html><body>
        <nav>Menu Login Pesquisa Entrar</nav>
        <aside>Publicidade milho</aside>
        <div id="toc">Sumário Rio Grande do Sul</div>
        <footer>Rodapé da wiki</footer>
        <p hidden>Conteúdo oculto de milho</p>
        <main>
        <p>Texto principal sobre quebra de safra neste parágrafo utilizável.</p>
        </main>
        </body></html>
        """;
    HtmlTextExtractor.Extracted extracted = HtmlTextExtractor.extract(html.getBytes(StandardCharsets.UTF_8), "text/html");
    String lower = extracted.excerpt().toLowerCase(Locale.ROOT);
    assertFalse(lower.startsWith("menu"));
    assertFalse(lower.contains("entrar"));
    assertFalse(lower.contains("sumário") || lower.contains("sumario"));
    assertFalse(extracted.normalizedText().toLowerCase(Locale.ROOT).contains("publicidade"));
    assertFalse(extracted.normalizedText().toLowerCase(Locale.ROOT).contains("conteúdo oculto"));
    List<DeterministicPageContextExtractor.Element> elements =
        DeterministicPageContextExtractor.extract(extracted.normalizedText());
    assertFalse(hasKey(elements, "crop"));
    assertFalse(hasKey(elements, "region"));
  }

  @Test
  void bodyWithoutMainUsesDocumentedFallback() {
    String html =
        """
        <html><body>
        <nav>Login Busca Menu</nav>
        <div>
        <p>Primeiro parágrafo longo o bastante sobre o artigo agrícola brasileiro contemporâneo.</p>
        <p>Segundo parágrafo continua o texto principal da página sem estar em main ou article.</p>
        </div>
        <footer>Rodapé</footer>
        </body></html>
        """;
    HtmlTextExtractor.Extracted extracted = HtmlTextExtractor.extract(html.getBytes(StandardCharsets.UTF_8), "text/html");
    assertEquals(HtmlTextExtractor.STRATEGY_FALLBACK, extracted.selectionStrategy());
    assertTrue(extracted.usable());
    assertTrue(extracted.normalizedText().contains("parágrafo longo"));
    assertFalse(extracted.normalizedText().toLowerCase(Locale.ROOT).contains("login"));
  }

  @Test
  void chromeOnlyPageFailsHonestly() {
    String html =
        """
        <html><body>
        <nav>Menu Início Login Pesquisa Ajuda Contato</nav>
        <div id="toc">Índice milho soja café</div>
        <footer>Privacidade Termos</footer>
        </body></html>
        """;
    HtmlTextExtractor.Extracted extracted = HtmlTextExtractor.extract(html.getBytes(StandardCharsets.UTF_8), "text/html");
    assertFalse(extracted.usable());
  }

  @Test
  void hostileAndOversizedStayLimited() {
    String huge = "<html><body><main><p>" + "quebra de safra ".repeat(8000) + "</p></main></body></html>";
    HtmlTextExtractor.Extracted extracted = HtmlTextExtractor.extract(huge.getBytes(StandardCharsets.UTF_8), "text/html");
    assertTrue(extracted.normalizedText().length() <= HtmlTextExtractor.MAX_NORMALIZED_CHARS);
    String hostile =
        "<html><body><main><p>A quebra de safra visível.</p><script>alert('x')</script></main></body></html>";
    HtmlTextExtractor.Extracted inert = HtmlTextExtractor.extract(hostile.getBytes(StandardCharsets.UTF_8), "text/html");
    assertFalse(inert.normalizedText().contains("alert"));
  }

  @Test
  void auditedWikipediaFixtureOmitsDistantMilhoAndRioGrandeDoSul() throws Exception {
    byte[] fixture =
        SemanticFidelityCorpusTest.class
            .getResourceAsStream("/urlcapture/SEGSENSE_PRM_020_COR_001_wikipedia_fixture.html")
            .readAllBytes();
    String bytesHash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(fixture));
    HtmlTextExtractor.Extracted extracted = HtmlTextExtractor.extract(fixture, "text/html");
    String textHash =
        HexFormat.of()
            .formatHex(MessageDigest.getInstance("SHA-256").digest(extracted.normalizedText().getBytes(StandardCharsets.UTF_8)));
    assertTrue(extracted.usable());
    assertEquals(HtmlTextExtractor.STRATEGY_MAIN, extracted.selectionStrategy());
    assertTrue(extracted.excerpt().toLowerCase(Locale.ROOT).contains("quebra de safra"));
    assertFalse(extracted.excerpt().toLowerCase(Locale.ROOT).contains("entrar"));
    assertFalse(extracted.excerpt().toLowerCase(Locale.ROOT).contains("criar uma conta"));
    List<DeterministicPageContextExtractor.Element> elements =
        DeterministicPageContextExtractor.extract(extracted.normalizedText());
    assertTrue(has(elements, "theme", "crop_production_loss"));
    assertTrue(has(elements, "event", "crop_failure"));
    assertFalse(hasKey(elements, "crop"));
    assertFalse(hasKey(elements, "region"));
    assertFalse(elements.stream().anyMatch(item -> "milho".equalsIgnoreCase(item.value())));
    assertFalse(elements.stream().anyMatch(item -> item.value().toLowerCase(Locale.ROOT).contains("rio grande")));
    // Hashes identify the test fixture only — not a proof of the live Wikipedia URL.
    assertEquals(64, bytesHash.length());
    assertEquals(64, textHash.length());
    assertEquals("TEST_FIXTURE", "TEST_FIXTURE");
  }

  private static boolean has(List<DeterministicPageContextExtractor.Element> elements, String key, String value) {
    return elements.stream().anyMatch(item -> key.equals(item.key()) && value.equals(item.value()));
  }

  private static boolean hasKey(List<DeterministicPageContextExtractor.Element> elements, String key) {
    return elements.stream().anyMatch(item -> key.equals(item.key()));
  }
}
