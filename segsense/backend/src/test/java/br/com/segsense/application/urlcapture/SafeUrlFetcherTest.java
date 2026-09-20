package br.com.segsense.application.urlcapture;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.net.InetAddress;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class SafeUrlFetcherTest {

  @Test
  void rejectsLoopbackLiteral() {
    UrlCaptureRejectedException error =
        assertThrows(UrlCaptureRejectedException.class, () -> fetcher(publicResolver(), unusedTransport()).fetch("http://127.0.0.1/"));
    assertEquals("DNS_BLOCKED", error.resultCode());
  }

  @Test
  void rejectsIpv6LoopbackLiteral() {
    UrlCaptureRejectedException error =
        assertThrows(
            UrlCaptureRejectedException.class,
            () -> fetcher(publicResolver(), unusedTransport()).fetch("http://[::1]/"));
    assertEquals("DNS_BLOCKED", error.resultCode());
  }

  @Test
  void rejectsMetadataIpv4() {
    UrlCaptureRejectedException error =
        assertThrows(
            UrlCaptureRejectedException.class,
            () -> fetcher(publicResolver(), unusedTransport()).fetch("http://169.254.169.254/latest/meta-data"));
    assertEquals("DNS_BLOCKED", error.resultCode());
  }

  @Test
  void rejectsPrivateRedirect() throws Exception {
    UrlFetchTransport transport =
        (uri, connect, read, max) -> {
          if (uri.getHost().contains("example")) {
            return new UrlFetchTransport.Response(302, "text/html", "http://192.168.0.10/secret", new byte[0], Map.of());
          }
          throw new IllegalStateException(uri.toString());
        };
    UrlCaptureRejectedException error =
        assertThrows(
            UrlCaptureRejectedException.class,
            () -> fetcher(publicResolver(), transport).fetch("https://example.test/article"));
    assertEquals("REDIRECT_BLOCKED", error.resultCode());
  }

  @Test
  void rejectsDnsRebinding() {
    AtomicInteger calls = new AtomicInteger();
    HostResolver rebinding =
        host -> {
          if (calls.getAndIncrement() == 0) {
            return new InetAddress[] {InetAddress.getByName("8.8.8.8")};
          }
          return new InetAddress[] {InetAddress.getByName("127.0.0.1")};
        };
    UrlCaptureRejectedException error =
        assertThrows(
            UrlCaptureRejectedException.class,
            () -> fetcher(rebinding, unusedTransport()).fetch("https://example.test/"));
    assertEquals("DNS_BLOCKED", error.resultCode());
  }

  @Test
  void fetchesHtmlAndStopsAtLimit() throws Exception {
    byte[] html =
        "<html lang=\"pt-BR\"><head><title>Quebra de safra</title></head><body><main><p>A quebra de safra de milho no Paraná em 2026 reduziu a produção agrícola.</p><script>alert(1)</script></main></body></html>"
            .getBytes(StandardCharsets.UTF_8);
    UrlFetchTransport transport =
        (uri, connect, read, max) -> new UrlFetchTransport.Response(200, "text/html; charset=utf-8", null, html, Map.of());
    SafeUrlFetcher.Outcome outcome = fetcher(publicResolver(), transport).fetch("https://example.test/safra");
    assertEquals("FETCHED", outcome.resultCode());
    assertEquals(200, outcome.httpStatus());
    HtmlTextExtractor.Extracted extracted = HtmlTextExtractor.extract(outcome.body(), outcome.contentType());
    assertTrue(extracted.normalizedText().contains("quebra de safra"));
    assertTrue(!extracted.normalizedText().contains("alert"));
    List<DeterministicPageContextExtractor.Element> elements =
        DeterministicPageContextExtractor.extract(extracted.normalizedText());
    assertTrue(elements.stream().anyMatch(item -> "crop_production_loss".equals(item.value())));
    assertTrue(elements.stream().anyMatch(item -> "milho".equals(item.value())));
  }

  @Test
  void rejectsUnsupportedMime() throws Exception {
    UrlFetchTransport transport =
        (uri, connect, read, max) ->
            new UrlFetchTransport.Response(200, "application/pdf", null, new byte[] {1, 2, 3}, Map.of());
    SafeUrlFetcher.Outcome outcome = fetcher(publicResolver(), transport).fetch("https://example.test/file.pdf");
    assertEquals("UNSUPPORTED_CONTENT", outcome.resultCode());
  }

  @Test
  void rejectsUserinfo() {
    UrlCaptureRejectedException error =
        assertThrows(
            UrlCaptureRejectedException.class,
            () -> fetcher(publicResolver(), unusedTransport()).fetch("https://user:pass@example.test/"));
    assertEquals("INVALID_URL", error.resultCode());
  }

  private static SafeUrlFetcher fetcher(HostResolver resolver, UrlFetchTransport transport) {
    return new SafeUrlFetcher(resolver, transport, 3, 1024, Duration.ofSeconds(1), Duration.ofSeconds(1));
  }

  private static HostResolver publicResolver() {
    return host -> new InetAddress[] {InetAddress.getByName("8.8.8.8")};
  }

  private static UrlFetchTransport unusedTransport() {
    return (uri, connect, read, max) -> {
      throw new IllegalStateException("transport should not run for " + uri);
    };
  }
}
