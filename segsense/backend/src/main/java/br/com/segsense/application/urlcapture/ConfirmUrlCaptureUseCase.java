package br.com.segsense.application.urlcapture;

import br.com.segsense.application.correlation.CorrelationContext;
import br.com.segsense.domain.demo.DemoProtectionException;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;

@Service
@Profile({"local", "test"})
@ConditionalOnProperty(name = "segsense.demo.protection-journey.enabled", havingValue = "true")
public class ConfirmUrlCaptureUseCase {

  private final UrlCaptureRepository captures;
  private final Clock clock;

  @Autowired
  public ConfirmUrlCaptureUseCase(UrlCaptureRepository captures) {
    this(captures, Clock.systemUTC());
  }

  ConfirmUrlCaptureUseCase(UrlCaptureRepository captures, Clock clock) {
    this.captures = captures;
    this.clock = clock;
  }

  public UrlCaptureConfirmationRecord execute(UUID captureId, Map<String, ?> body) {
    UrlCaptureRecord capture =
        captures
            .findCapture(captureId)
            .orElseThrow(() -> new DemoProtectionException("NOT_FOUND", 404, "Captura não encontrada."));
    if (!"FETCHED".equals(capture.resultCode())) {
      throw new DemoProtectionException(
          "CAPTURE_NOT_REVIEWABLE",
          409,
          "Só é possível confirmar um conteúdo obtido com texto suficiente.");
    }
    Instant now = clock.instant();
    String correlation =
        CorrelationContext.current() == null ? captureId.toString() : CorrelationContext.current().toString();
    List<Map<String, String>> original = UrlExtractedEnvelope.readElementList(capture.extractedElementsJson());
    Set<String> confirmedKeys = confirmedKeys(body, original);
    Map<String, String> corrections = correctionsOf(body);
    List<Map<String, String>> confirmed = new ArrayList<>();
    List<Map<String, String>> declared = new ArrayList<>();
    for (Map<String, String> element : original) {
      String key = element.get("key");
      if (key == null || !confirmedKeys.contains(key)) {
        continue;
      }
      if (!UrlExtractedEnvelope.evidenceSupported(capture.normalizedText(), element, capture.extractorVersion())) {
        continue;
      }
      String originalValue = element.get("value");
      String corrected = corrections.get(key);
      if (corrected != null && !corrected.isBlank() && !corrected.equals(originalValue)) {
        Map<String, String> item = declaredItem(key, corrected);
        declared.add(item);
        confirmed.add(item);
      } else {
        confirmed.add(element);
      }
    }
    for (Map.Entry<String, String> extra : corrections.entrySet()) {
      if (extra.getValue() == null || extra.getValue().isBlank() || "url".equals(extra.getKey())) {
        continue;
      }
      if (confirmedKeys.contains(extra.getKey())) {
        continue;
      }
      Map<String, String> item = declaredItem(clip(extra.getKey(), 40), extra.getValue());
      declared.add(item);
      confirmed.add(item);
    }
    UrlCaptureConfirmationRecord record =
        new UrlCaptureConfirmationRecord(
            UUID.randomUUID(),
            captureId,
            now,
            UrlExtractedEnvelope.writeElements(confirmed),
            UrlExtractedEnvelope.writeElements(declared),
            correlation);
    captures.insertConfirmation(record);
    return record;
  }

  private static Map<String, String> declaredItem(String key, String value) {
    Map<String, String> item = new LinkedHashMap<>();
    item.put("key", key);
    item.put("value", clip(value, 200));
    item.put("evidence", "");
    item.put("origin", UrlExtractedEnvelope.ORIGIN_DECLARED);
    item.put("rule", "USER_DECLARED");
    item.put("startOffset", "");
    item.put("endOffset", "");
    item.put("windowKind", "");
    return item;
  }

  private static Set<String> confirmedKeys(Map<String, ?> body, List<Map<String, String>> original) {
    Object raw = body == null ? null : body.get("confirmedKeys");
    Set<String> keys = new LinkedHashSet<>();
    if (raw instanceof List<?> list) {
      for (Object item : list) {
        if (item != null && !String.valueOf(item).isBlank()) {
          keys.add(String.valueOf(item));
        }
      }
      return keys;
    }
    if (raw instanceof String text && !text.isBlank()) {
      for (String part : text.split(",")) {
        if (!part.isBlank()) {
          keys.add(part.trim());
        }
      }
      return keys;
    }
    for (Map<String, String> element : original) {
      if (element.get("key") != null && !element.get("key").isBlank()) {
        keys.add(element.get("key"));
      }
    }
    return keys;
  }

  @SuppressWarnings("unchecked")
  private static Map<String, String> correctionsOf(Map<String, ?> body) {
    Map<String, String> corrections = new LinkedHashMap<>();
    if (body == null) {
      return corrections;
    }
    Object nested = body.get("corrections");
    if (nested instanceof Map<?, ?> map) {
      for (Map.Entry<?, ?> entry : map.entrySet()) {
        if (entry.getValue() != null && !String.valueOf(entry.getValue()).isBlank()) {
          corrections.put(String.valueOf(entry.getKey()), String.valueOf(entry.getValue()).trim());
        }
      }
    }
    for (Map.Entry<String, ?> entry : body.entrySet()) {
      if ("confirmedKeys".equals(entry.getKey()) || "corrections".equals(entry.getKey())) {
        continue;
      }
      if (entry.getValue() instanceof String value && !value.isBlank()) {
        corrections.put(entry.getKey(), value.trim());
      }
    }
    return corrections;
  }

  private static String clip(String value, int max) {
    String trimmed = value.trim();
    return trimmed.length() <= max ? trimmed : trimmed.substring(0, max);
  }
}
