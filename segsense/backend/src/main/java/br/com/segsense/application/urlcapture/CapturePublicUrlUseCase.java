package br.com.segsense.application.urlcapture;

import br.com.segsense.application.correlation.CorrelationContext;
import br.com.segsense.application.demo.DemoProjectionJson;
import br.com.segsense.domain.demo.DemoProtectionException;
import java.net.InetAddress;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;

@Service
@Profile({"local", "test"})
@ConditionalOnProperty(name = "segsense.demo.protection-journey.enabled", havingValue = "true")
public class CapturePublicUrlUseCase {

  private static final Logger log = LoggerFactory.getLogger(CapturePublicUrlUseCase.class);
  private final UrlCaptureRepository captures;
  private final Clock clock;
  private final SafeUrlFetcher fetcher;

  @Autowired
  public CapturePublicUrlUseCase(
      UrlCaptureRepository captures,
      @Value("${segsense.demo.url-capture.max-bytes:1048576}") int maxBytes,
      @Value("${segsense.demo.url-capture.max-redirects:3}") int maxRedirects,
      @Value("${segsense.demo.url-capture.connect-timeout:PT5S}") Duration connectTimeout,
      @Value("${segsense.demo.url-capture.read-timeout:PT8S}") Duration readTimeout) {
    this(
        captures,
        Clock.systemUTC(),
        new SafeUrlFetcher(
            CapturePublicUrlUseCase::resolve,
            new JdkUrlFetchTransport(connectTimeout),
            maxRedirects,
            maxBytes,
            connectTimeout,
            readTimeout));
  }

  CapturePublicUrlUseCase(UrlCaptureRepository captures, Clock clock, SafeUrlFetcher fetcher) {
    this.captures = captures;
    this.clock = clock;
    this.fetcher = fetcher;
  }

  public UrlCaptureRecord execute(String rawUrl) {
    Instant now = clock.instant();
    UUID id = UUID.randomUUID();
    String correlation =
        CorrelationContext.current() == null ? id.toString() : CorrelationContext.current().toString();
    try {
      SafeUrlFetcher.Outcome outcome = fetcher.fetch(rawUrl);
      if (!"FETCHED".equals(outcome.resultCode())) {
        return persistFailure(
            id, now, correlation, rawUrl, outcome, outcome.resultCode(), null, null);
      }
      HtmlTextExtractor.Extracted extracted =
          HtmlTextExtractor.extract(outcome.body(), outcome.contentType());
      if (!extracted.usable()) {
        return persistFailure(
            id,
            now,
            correlation,
            rawUrl,
            outcome,
            "NO_MEANINGFUL_TEXT",
            extracted,
            sha256(outcome.body()));
      }
      List<DeterministicPageContextExtractor.Element> elements =
          DeterministicPageContextExtractor.extract(extracted.normalizedText());
      UrlCaptureRecord record =
          new UrlCaptureRecord(
              id,
              clipUrl(rawUrl),
              outcome.finalUri() == null ? clipUrl(rawUrl) : clipUrl(outcome.finalUri().toString()),
              outcome.finalUri() == null ? null : outcome.finalUri().getHost(),
              now,
              outcome.httpStatus(),
              outcome.contentType(),
              extracted.title(),
              extracted.language(),
              extracted.excerpt(),
              extracted.normalizedText(),
              sha256(outcome.body()),
              sha256(extracted.normalizedText().getBytes(StandardCharsets.UTF_8)),
              HtmlTextExtractor.VERSION,
              "FETCHED",
              json(DeterministicPageContextExtractor.asPublicDocument(elements, extracted.selectionStrategy())),
              correlation,
              now);
      captures.insertCapture(record);
      logSafe(record);
      return record;
    } catch (UrlCaptureRejectedException rejected) {
      UrlCaptureRecord record =
          new UrlCaptureRecord(
              id,
              clipUrl(rawUrl),
              null,
              null,
              now,
              null,
              null,
              "",
              "",
              "",
              "",
              null,
              null,
              HtmlTextExtractor.VERSION,
              rejected.resultCode(),
              json(Map.of("elements", List.of())),
              correlation,
              now);
      captures.insertCapture(record);
      logSafe(record);
      return record;
    } catch (RuntimeException unexpected) {
      UrlCaptureRecord record =
          new UrlCaptureRecord(
              id,
              clipUrl(rawUrl),
              null,
              null,
              now,
              null,
              null,
              "",
              "",
              "",
              "",
              null,
              null,
              HtmlTextExtractor.VERSION,
              "INVALID_URL",
              json(Map.of("elements", List.of())),
              correlation,
              now);
      captures.insertCapture(record);
      logSafe(record);
      return record;
    }
  }

  private UrlCaptureRecord persistFailure(
      UUID id,
      Instant now,
      String correlation,
      String rawUrl,
      SafeUrlFetcher.Outcome outcome,
      String resultCode,
      HtmlTextExtractor.Extracted extracted,
      String bytesHash) {
    UrlCaptureRecord record =
        new UrlCaptureRecord(
            id,
            clipUrl(rawUrl),
            outcome.finalUri() == null ? null : clipUrl(outcome.finalUri().toString()),
            outcome.finalUri() == null ? null : outcome.finalUri().getHost(),
            now,
            outcome.httpStatus() == 0 ? null : outcome.httpStatus(),
            outcome.contentType(),
            extracted == null ? "" : extracted.title(),
            extracted == null ? "" : extracted.language(),
            "NO_MEANINGFUL_TEXT".equals(resultCode) ? "" : extracted == null ? "" : extracted.excerpt(),
            "NO_MEANINGFUL_TEXT".equals(resultCode) ? "" : extracted == null ? "" : extracted.normalizedText(),
            bytesHash,
            "NO_MEANINGFUL_TEXT".equals(resultCode)
                    || extracted == null
                    || extracted.normalizedText() == null
                    || extracted.normalizedText().isBlank()
                ? null
                : sha256(extracted.normalizedText().getBytes(StandardCharsets.UTF_8)),
            HtmlTextExtractor.VERSION,
            resultCode,
            json(
                Map.of(
                    "selectionStrategy",
                    extracted == null ? HtmlTextExtractor.STRATEGY_NONE : extracted.selectionStrategy(),
                    "extractorRuleSet",
                    DeterministicPageContextExtractor.RULE_SET,
                    "elements",
                    List.of())),
            correlation,
            now);
    captures.insertCapture(record);
    logSafe(record);
    return record;
  }

  public UrlCaptureRecord require(UUID id) {
    return captures
        .findCapture(id)
        .orElseThrow(() -> new DemoProtectionException("NOT_FOUND", 404, "Captura não encontrada."));
  }

  private static InetAddress[] resolve(String host) throws java.net.UnknownHostException {
    return InetAddress.getAllByName(host);
  }

  private static String clipUrl(String value) {
    if (value == null) {
      return "";
    }
    String trimmed = value.trim();
    return trimmed.length() <= 2048 ? trimmed : trimmed.substring(0, 2048);
  }

  private static String sha256(byte[] value) {
    try {
      return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value == null ? new byte[0] : value));
    } catch (NoSuchAlgorithmException e) {
      throw new IllegalStateException(e);
    }
  }

  private String json(Object value) {
    if (value instanceof Map<?, ?> map) {
      Map<String, Object> typed = new java.util.LinkedHashMap<>();
      map.forEach((key, item) -> typed.put(String.valueOf(key), item));
      return DemoProjectionJson.write(typed);
    }
    return "{\"elements\":[]}";
  }

  private static void logSafe(UrlCaptureRecord record) {
    String host = record.finalHost() == null ? "" : record.finalHost().replaceAll("[\\r\\n\\t]", "_");
    log.info(
        "event=url_capture result={} host={} captureId={}",
        record.resultCode(),
        host,
        record.id());
  }
}
