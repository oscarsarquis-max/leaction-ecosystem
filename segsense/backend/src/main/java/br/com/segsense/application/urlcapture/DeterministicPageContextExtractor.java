package br.com.segsense.application.urlcapture;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * LOCAL_WINDOW_V1: associate crop/region/period only inside the same paragraph as the event phrase.
 * Distant index, caption, bibliography or institutional history is omitted.
 */
public final class DeterministicPageContextExtractor {

  public static final String RULE_SET = "LOCAL_WINDOW_V1";
  public static final String WINDOW_PARAGRAPH = "PARAGRAPH";

  private DeterministicPageContextExtractor() {}

  public record Element(
      String key,
      String value,
      String evidence,
      String origin,
      String rule,
      int startOffset,
      int endOffset,
      String windowKind) {}

  public static List<Element> extract(String normalizedText) {
    List<Element> elements = new ArrayList<>();
    if (normalizedText == null || normalizedText.isBlank()) {
      return List.of();
    }
    List<Paragraph> paragraphs = paragraphs(normalizedText);
    List<Hit> events = eventHits(paragraphs);
    if (events.isEmpty()) {
      return List.of();
    }
    Hit first = events.get(0);
    elements.add(
        element("theme", "crop_production_loss", first, "EVENT_PHRASE_IN_PARAGRAPH"));
    elements.add(element("event", "crop_failure", first, "EVENT_PHRASE_IN_PARAGRAPH"));
    elements.add(
        element("situation", "crop_failure_reported", first, "EVENT_PHRASE_IN_PARAGRAPH"));
    elements.add(
        element("constraint", "editorial_not_eligibility", first, "EVENT_PHRASE_IN_PARAGRAPH"));
    addUniqueAssociated(
        elements,
        associatedInEventParagraphs(paragraphs, events, crops()),
        "crop",
        "CROP_IN_SAME_PARAGRAPH_AS_EVENT");
    addUniqueAssociated(
        elements,
        associatedInEventParagraphs(paragraphs, events, regions()),
        "region",
        "REGION_IN_SAME_PARAGRAPH_AS_EVENT");
    addUniqueAssociated(
        elements,
        associatedInEventParagraphs(paragraphs, events, periods()),
        "period",
        "PERIOD_IN_SAME_PARAGRAPH_AS_EVENT");
    return List.copyOf(elements);
  }

  public static Map<String, Object> asPublicDocument(List<Element> elements, String selectionStrategy) {
    Map<String, Object> root = new LinkedHashMap<>();
    root.put("selectionStrategy", selectionStrategy == null ? "" : selectionStrategy);
    root.put("extractorRuleSet", RULE_SET);
    root.put("windowKind", WINDOW_PARAGRAPH);
    List<Map<String, String>> items = new ArrayList<>();
    for (Element element : elements) {
      items.add(toMap(element));
    }
    root.put("elements", items);
    return root;
  }

  public static Map<String, Object> asPublicList(List<Element> elements) {
    return asPublicDocument(elements, "");
  }

  static Map<String, String> toMap(Element element) {
    Map<String, String> item = new LinkedHashMap<>();
    item.put("key", element.key());
    item.put("value", element.value());
    item.put("evidence", element.evidence());
    item.put("origin", element.origin());
    item.put("rule", element.rule());
    item.put("startOffset", Integer.toString(element.startOffset()));
    item.put("endOffset", Integer.toString(element.endOffset()));
    item.put("windowKind", element.windowKind());
    return item;
  }

  private static void addUniqueAssociated(
      List<Element> elements, List<Associated> found, String key, String rule) {
    Set<String> values = new LinkedHashSet<>();
    for (Associated item : found) {
      values.add(item.value());
    }
    if (values.size() != 1) {
      return;
    }
    Associated only = found.get(0);
    elements.add(
        new Element(
            key,
            only.value(),
            only.evidence(),
            "URL_EXTRACTED",
            rule,
            only.startOffset(),
            only.endOffset(),
            WINDOW_PARAGRAPH));
  }

  private static List<Associated> associatedInEventParagraphs(
      List<Paragraph> paragraphs, List<Hit> events, String[][] needles) {
    Set<Integer> eventParagraphs = new LinkedHashSet<>();
    for (Hit event : events) {
      eventParagraphs.add(event.paragraphIndex());
    }
    List<Associated> found = new ArrayList<>();
    for (int index : eventParagraphs) {
      Paragraph paragraph = paragraphs.get(index);
      Hit event = firstEventIn(events, index);
      for (String[] needle : needles) {
        int local = indexOfWord(paragraph.lower(), needle[0]);
        if (local < 0) {
          continue;
        }
        int start = paragraph.start() + local;
        int end = start + needle[0].length();
        found.add(
            new Associated(
                needle[1],
                relationSnippet(paragraph.text(), event.localStart(), event.needleLength(), local, needle[0].length()),
                start,
                end));
        break;
      }
    }
    return found;
  }

  private static Hit firstEventIn(List<Hit> events, int paragraphIndex) {
    for (Hit event : events) {
      if (event.paragraphIndex() == paragraphIndex) {
        return event;
      }
    }
    return events.get(0);
  }

  private static List<Hit> eventHits(List<Paragraph> paragraphs) {
    String[] cropFailure = {
      "quebra de safra",
      "quebra da safra",
      "perda de produção",
      "perda de producao",
      "perda de produtividade"
    };
    List<Hit> hits = new ArrayList<>();
    for (int i = 0; i < paragraphs.size(); i++) {
      Paragraph paragraph = paragraphs.get(i);
      for (String needle : cropFailure) {
        int local = paragraph.lower().indexOf(needle);
        if (local >= 0) {
          hits.add(
              new Hit(
                  i,
                  paragraph.start() + local,
                  paragraph.start() + local + needle.length(),
                  local,
                  needle.length(),
                  snippet(paragraph.text(), local, needle.length())));
          break;
        }
      }
    }
    return hits;
  }

  private static Element element(String key, String value, Hit hit, String rule) {
    return new Element(
        key, value, hit.evidence(), "URL_EXTRACTED", rule, hit.startOffset(), hit.endOffset(), WINDOW_PARAGRAPH);
  }

  private static String[][] crops() {
    return new String[][] {
      {"milho", "milho"},
      {"soja", "soja"},
      {"café", "café"},
      {"cafe", "café"},
      {"trigo", "trigo"},
      {"arroz", "arroz"}
    };
  }

  private static String[][] regions() {
    return new String[][] {
      {"rio grande do sul", "Rio Grande do Sul"},
      {"mato grosso do sul", "Mato Grosso do Sul"},
      {"mato grosso", "Mato Grosso"},
      {"minas gerais", "Minas Gerais"},
      {"santa catarina", "Santa Catarina"},
      {"paraná", "Paraná"},
      {"parana", "Paraná"},
      {"goiás", "Goiás"},
      {"goias", "Goiás"},
      {"bahia", "Bahia"},
      {"são paulo", "São Paulo"},
      {"sao paulo", "São Paulo"}
    };
  }

  private static String[][] periods() {
    return new String[][] {{"2026", "2026"}, {"2025", "2025"}, {"2024", "2024"}};
  }

  private static List<Paragraph> paragraphs(String text) {
    List<Paragraph> items = new ArrayList<>();
    int i = 0;
    while (i < text.length()) {
      while (i < text.length() && Character.isWhitespace(text.charAt(i))) {
        i++;
      }
      if (i >= text.length()) {
        break;
      }
      int start = i;
      int blank = text.indexOf("\n\n", i);
      int end = blank < 0 ? text.length() : blank;
      String body = text.substring(start, end).trim();
      if (!body.isBlank()) {
        items.add(new Paragraph(start, body, body.toLowerCase(Locale.ROOT)));
      }
      i = end + 2;
    }
    if (items.isEmpty() && !text.isBlank()) {
      String body = text.trim();
      items.add(new Paragraph(0, body, body.toLowerCase(Locale.ROOT)));
    }
    return items;
  }

  private static int indexOfWord(String lower, String needle) {
    int from = 0;
    while (from < lower.length()) {
      int idx = lower.indexOf(needle, from);
      if (idx < 0) {
        return -1;
      }
      boolean before = idx == 0 || !Character.isLetterOrDigit(lower.charAt(idx - 1));
      int end = idx + needle.length();
      boolean after = end >= lower.length() || !Character.isLetterOrDigit(lower.charAt(end));
      if (before && after) {
        return idx;
      }
      from = idx + 1;
    }
    return -1;
  }

  private static String snippet(String original, int idx, int length) {
    int start = Math.max(0, idx - 40);
    int end = Math.min(original.length(), idx + length + 40);
    return original.substring(start, end).trim();
  }

  private static String relationSnippet(
      String paragraph, int eventStart, int eventLen, int otherStart, int otherLen) {
    int start = Math.min(eventStart, otherStart);
    int end = Math.max(eventStart + eventLen, otherStart + otherLen);
    int from = Math.max(0, start - 48);
    int to = Math.min(paragraph.length(), end + 48);
    String clipped = paragraph.substring(from, to).trim();
    return clipped.length() <= 240 ? clipped : clipped.substring(0, 240);
  }

  private record Paragraph(int start, String text, String lower) {}

  private record Hit(
      int paragraphIndex, int startOffset, int endOffset, int localStart, int needleLength, String evidence) {}

  private record Associated(String value, String evidence, int startOffset, int endOffset) {}
}
