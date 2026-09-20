package br.com.segsense.application.urlcapture;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.segsense.application.demo.DemoProjectionJson;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class ConfirmUrlCaptureUseCaseTest {

  @Test
  void omittedKeysStayOutOfConfirmedPayloadAndDeclaredCropIsSeparate() {
    String text = "A quebra de safra de milho no Paraná em 2026 reduziu a produção.";
    List<DeterministicPageContextExtractor.Element> extracted =
        DeterministicPageContextExtractor.extract(text);
    UUID captureId = UUID.fromString("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
    UrlCaptureRecord capture =
        new UrlCaptureRecord(
            captureId,
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
            DemoProjectionJson.write(
                DeterministicPageContextExtractor.asPublicDocument(extracted, HtmlTextExtractor.STRATEGY_MAIN)),
            "corr",
            Instant.parse("2026-09-15T12:00:00Z"));
    MemoryRepo repo = new MemoryRepo(capture);
    ConfirmUrlCaptureUseCase useCase = new ConfirmUrlCaptureUseCase(repo);
    UrlCaptureConfirmationRecord confirmation =
        useCase.execute(
            captureId,
            Map.of(
                "confirmedKeys",
                List.of("theme", "event", "situation", "constraint"),
                "corrections",
                Map.of("crop", "soja"),
                "declaredNote",
                "Complemento da pessoa."));
    List<Map<String, String>> confirmed = UrlExtractedEnvelope.readElementList(confirmation.confirmedElementsJson());
    List<Map<String, String>> declared = UrlExtractedEnvelope.readElementList(confirmation.correctionsJson());
    assertTrue(confirmed.stream().noneMatch(item -> "milho".equals(item.get("value"))));
    assertTrue(confirmed.stream().anyMatch(item -> "theme".equals(item.get("key"))));
    assertTrue(
        declared.stream()
            .anyMatch(
                item ->
                    "crop".equals(item.get("key"))
                        && "soja".equals(item.get("value"))
                        && "USER_DECLARED".equals(item.get("origin"))));
    assertEquals("USER_DECLARED", declared.stream().filter(item -> "declaredNote".equals(item.get("key"))).findFirst().orElseThrow().get("origin"));
    Map<String, Object> contribution = UrlExtractedEnvelope.urlContribution(capture, confirmed);
    @SuppressWarnings("unchecked")
    Map<String, String> spiderElements = (Map<String, String>) contribution.get("elements");
    assertEquals("crop_production_loss", spiderElements.get("theme"));
    org.junit.jupiter.api.Assertions.assertFalse(spiderElements.containsKey("crop"));
    org.junit.jupiter.api.Assertions.assertFalse(spiderElements.containsKey("region"));
  }

  private static final class MemoryRepo implements UrlCaptureRepository {
    private final UrlCaptureRecord capture;
    private UrlCaptureConfirmationRecord confirmation;

    private MemoryRepo(UrlCaptureRecord capture) {
      this.capture = capture;
    }

    @Override
    public void insertCapture(UrlCaptureRecord record) {}

    @Override
    public Optional<UrlCaptureRecord> findCapture(UUID id) {
      return capture.id().equals(id) ? Optional.of(capture) : Optional.empty();
    }

    @Override
    public void insertConfirmation(UrlCaptureConfirmationRecord record) {
      this.confirmation = record;
    }

    @Override
    public Optional<UrlCaptureConfirmationRecord> findLatestConfirmation(UUID captureId) {
      return Optional.ofNullable(confirmation);
    }

    @Override
    public List<UrlCaptureConfirmationRecord> confirmationsOf(UUID captureId) {
      return confirmation == null ? List.of() : List.of(confirmation);
    }
  }
}
