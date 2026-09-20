package br.com.segsense.application.urlcapture;

import java.net.InetAddress;
import java.net.URI;
import java.net.UnknownHostException;
import java.time.Duration;
import java.util.Arrays;
import java.util.Locale;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.TimeoutException;
import java.util.stream.Collectors;

public final class SafeUrlFetcher {

  public static final int DEFAULT_MAX_REDIRECTS = 3;
  public static final int DEFAULT_MAX_BYTES = 1_048_576;
  public static final Duration DEFAULT_CONNECT = Duration.ofSeconds(5);
  public static final Duration DEFAULT_READ = Duration.ofSeconds(8);

  private final HostResolver resolver;
  private final UrlFetchTransport transport;
  private final int maxRedirects;
  private final int maxBytes;
  private final Duration connectTimeout;
  private final Duration readTimeout;

  public SafeUrlFetcher(HostResolver resolver, UrlFetchTransport transport) {
    this(resolver, transport, DEFAULT_MAX_REDIRECTS, DEFAULT_MAX_BYTES, DEFAULT_CONNECT, DEFAULT_READ);
  }

  public SafeUrlFetcher(
      HostResolver resolver,
      UrlFetchTransport transport,
      int maxRedirects,
      int maxBytes,
      Duration connectTimeout,
      Duration readTimeout) {
    this.resolver = resolver;
    this.transport = transport;
    this.maxRedirects = maxRedirects;
    this.maxBytes = maxBytes;
    this.connectTimeout = connectTimeout;
    this.readTimeout = readTimeout;
  }

  public record Outcome(
      String resultCode,
      URI requested,
      URI finalUri,
      int httpStatus,
      String contentType,
      byte[] body) {}

  public Outcome fetch(String rawUrl) {
    PublicUrlParser.Parsed parsed = PublicUrlParser.parse(rawUrl);
    URI current = parsed.uri();
    URI requested = current;
    try {
      for (int hop = 0; hop <= maxRedirects; hop++) {
        try {
          assertPublicTarget(current);
        } catch (UrlCaptureRejectedException rejected) {
          if (hop > 0) {
            throw new UrlCaptureRejectedException(
                "REDIRECT_BLOCKED", "O redirecionamento desta página não é seguro para captura.");
          }
          throw rejected;
        }
        UrlFetchTransport.Response response =
            transport.get(current, connectTimeout, readTimeout, maxBytes);
        if (isRedirect(response.status())) {
          if (hop == maxRedirects) {
            return new Outcome("REDIRECT_BLOCKED", requested, current, response.status(), response.contentType(), new byte[0]);
          }
          current = nextLocation(current, response.location());
          continue;
        }
        if (response.status() < 200 || response.status() >= 300) {
          return new Outcome("HTTP_ERROR", requested, current, response.status(), response.contentType(), new byte[0]);
        }
        if (response.body() != null && response.body().length > maxBytes) {
          return new Outcome("TOO_LARGE", requested, current, response.status(), response.contentType(), new byte[0]);
        }
        if (!mimeAllowed(response.contentType())) {
          return new Outcome(
              "UNSUPPORTED_CONTENT", requested, current, response.status(), response.contentType(), new byte[0]);
        }
        return new Outcome("FETCHED", requested, current, response.status(), response.contentType(), response.body());
      }
      return new Outcome("REDIRECT_BLOCKED", requested, current, 0, "", new byte[0]);
    } catch (UrlCaptureRejectedException rejected) {
      throw rejected;
    } catch (UnknownHostException unknown) {
      throw new UrlCaptureRejectedException(
          "DNS_BLOCKED", "Este endereço não é uma página pública utilizável nesta demonstração.");
    } catch (TimeoutException | java.net.http.HttpTimeoutException timeout) {
      throw new UrlCaptureRejectedException("TIMEOUT", "A página não respondeu a tempo.");
    } catch (InterruptedException interrupted) {
      Thread.currentThread().interrupt();
      throw new UrlCaptureRejectedException("TIMEOUT", "A página não respondeu a tempo.");
    } catch (Exception failure) {
      String name = failure.getClass().getSimpleName().toLowerCase(Locale.ROOT);
      if (name.contains("timeout") || (failure.getCause() != null && failure.getCause() instanceof TimeoutException)) {
        throw new UrlCaptureRejectedException("TIMEOUT", "A página não respondeu a tempo.");
      }
      throw new UrlCaptureRejectedException(
          "HTTP_ERROR", "A página não devolveu conteúdo utilizável.");
    }
  }

  void assertPublicTarget(URI uri) throws UnknownHostException {
    PublicUrlParser.Parsed parsed = PublicUrlParser.parse(uri.toString());
    String host = parsed.host();
    if (looksLikeIp(host)) {
      InetAddress literal = InetAddress.getByName(host);
      if (PublicAddressClassifier.isBlocked(literal)) {
        throw new UrlCaptureRejectedException(
            "DNS_BLOCKED", "Este endereço não é uma página pública utilizável nesta demonstração.");
      }
      return;
    }
    InetAddress[] first = requirePublic(resolver.resolve(host));
    InetAddress[] second = requirePublic(resolver.resolve(host));
    if (!sameAddresses(first, second)) {
      throw new UrlCaptureRejectedException(
          "DNS_BLOCKED", "Este endereço não é uma página pública utilizável nesta demonstração.");
    }
  }

  private InetAddress[] requirePublic(InetAddress[] addresses) {
    if (addresses == null || addresses.length == 0) {
      throw new UrlCaptureRejectedException(
          "DNS_BLOCKED", "Este endereço não é uma página pública utilizável nesta demonstração.");
    }
    for (InetAddress address : addresses) {
      if (PublicAddressClassifier.isBlocked(address)) {
        throw new UrlCaptureRejectedException(
            "DNS_BLOCKED", "Este endereço não é uma página pública utilizável nesta demonstração.");
      }
    }
    return addresses;
  }

  private static boolean sameAddresses(InetAddress[] first, InetAddress[] second) {
    Set<String> left = Arrays.stream(first).map(a -> a.getHostAddress()).collect(Collectors.toCollection(TreeSet::new));
    Set<String> right = Arrays.stream(second).map(a -> a.getHostAddress()).collect(Collectors.toCollection(TreeSet::new));
    return left.equals(right);
  }

  private URI nextLocation(URI current, String location) {
    if (location == null || location.isBlank()) {
      throw new UrlCaptureRejectedException("REDIRECT_BLOCKED", "O redirecionamento desta página não é seguro para captura.");
    }
    URI resolved;
    try {
      resolved = current.resolve(location.trim());
    } catch (IllegalArgumentException invalid) {
      throw new UrlCaptureRejectedException("REDIRECT_BLOCKED", "O redirecionamento desta página não é seguro para captura.");
    }
    try {
      PublicUrlParser.parse(resolved.toString());
    } catch (UrlCaptureRejectedException rejected) {
      throw new UrlCaptureRejectedException("REDIRECT_BLOCKED", "O redirecionamento desta página não é seguro para captura.");
    }
    return PublicUrlParser.parse(resolved.toString()).uri();
  }

  private static boolean isRedirect(int status) {
    return status == 301 || status == 302 || status == 303 || status == 307 || status == 308;
  }

  static boolean mimeAllowed(String contentType) {
    if (contentType == null || contentType.isBlank()) {
      return false;
    }
    String mime = contentType.split(";", 2)[0].trim().toLowerCase(Locale.ROOT);
    return "text/html".equals(mime) || "application/xhtml+xml".equals(mime) || "text/plain".equals(mime);
  }

  private static boolean looksLikeIp(String host) {
    String value = host.replace("[", "").replace("]", "");
    return value.chars().allMatch(ch -> Character.isDigit(ch) || ch == '.' || ch == ':');
  }
}
