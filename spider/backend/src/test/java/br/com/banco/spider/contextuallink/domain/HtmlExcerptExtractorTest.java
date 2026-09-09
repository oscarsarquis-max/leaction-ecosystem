package br.com.banco.spider.contextuallink.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class HtmlExcerptExtractorTest {

  @Test
  void extractsEditorialFieldsAndIgnoresScripts() {
    String html =
        """
        <html><head><title>Safra</title>
        <meta name="description" content="Quebra de safra" />
        <script>window.intent='credit'</script></head>
        <body><article><p>Texto editorial relevante.</p></article></body></html>
        """;
    var excerpt = HtmlExcerptExtractor.extract(html);
    assertEquals("Safra", excerpt.title());
    assertEquals("Quebra de safra", excerpt.description());
    assertEquals("Texto editorial relevante.", excerpt.text());
    assertFalse(excerpt.text().contains("credit"));
  }

  @Test
  void extractsTheCampoAbertoReportagem() throws Exception {
    String html =
        new org.springframework.core.io.ClassPathResource("demo/partner/agro-hoje.html")
            .getContentAsString(java.nio.charset.StandardCharsets.UTF_8);
    var excerpt = HtmlExcerptExtractor.extract(html);
    assertTrue(excerpt.title().contains("Quebra de safra aperta o caixa"));
    assertTrue(excerpt.description().contains("receita menor"));
    assertTrue(excerpt.text().contains("Receita cai, mas o próximo ciclo não espera"));
    assertTrue(excerpt.text().contains("semente"));
    assertTrue(excerpt.text().contains("fertilizante"));
    assertFalse(excerpt.text().contains("{{GATEWAY_URL}}"));
  }
}
