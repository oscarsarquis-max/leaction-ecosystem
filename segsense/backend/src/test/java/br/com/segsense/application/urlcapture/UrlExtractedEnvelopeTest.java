package br.com.segsense.application.urlcapture;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class UrlExtractedEnvelopeTest {

  @Test
  void urlContributionOmitsUnconfirmedAndUnsupportedAttributes() {
    String text = "Houve quebra de safra neste parágrafo.\n\nOutro parágrafo cita milho.";
    List<DeterministicPageContextExtractor.Element> extracted =
        DeterministicPageContextExtractor.extract(text);
    UrlCaptureRecord capture =
        new UrlCaptureRecord(
            UUID.fromString("11111111-1111-1111-1111-111111111111"),
            "https://example.test/a",
            "https://example.test/a",
            "example.test",
            Instant.parse("2026-09-15T12:00:00Z"),
            200,
            "text/html",
            "t",
            "pt",
            text,
            text,
            "aa".repeat(32),
            "bb".repeat(32),
            HtmlTextExtractor.VERSION,
            "FETCHED",
            documentJson(extracted),
            "corr",
            Instant.parse("2026-09-15T12:00:00Z"));
    List<Map<String, String>> confirmed = UrlExtractedEnvelope.readElementList(capture.extractedElementsJson());
    confirmed.add(Map.of("key", "crop", "value", "milho", "evidence", "milho", "origin", "URL_EXTRACTED"));
    Map<String, Object> contribution = UrlExtractedEnvelope.urlContribution(capture, confirmed);
    @SuppressWarnings("unchecked")
    Map<String, String> elements = (Map<String, String>) contribution.get("elements");
    assertEquals("crop_production_loss", elements.get("theme"));
    assertFalse(elements.containsKey("crop"));
    assertFalse(elements.containsValue("milho"));
    assertTrue(UrlExtractedEnvelope.supportedUrlExtracted(capture, confirmed).stream()
        .noneMatch(item -> "crop".equals(item.get("key"))));
  }

  private static String documentJson(List<DeterministicPageContextExtractor.Element> extracted) {
    return br.com.segsense.application.demo.DemoProjectionJson.write(
        DeterministicPageContextExtractor.asPublicDocument(extracted, HtmlTextExtractor.STRATEGY_MAIN));
  }
}
