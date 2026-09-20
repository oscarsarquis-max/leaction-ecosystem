package br.com.segsense.application.urlcapture;

import java.net.URI;
import java.time.Duration;
import java.util.List;
import java.util.Map;

@FunctionalInterface
public interface UrlFetchTransport {

  record Response(
      int status,
      String contentType,
      String location,
      byte[] body,
      Map<String, List<String>> headers) {}

  Response get(URI uri, Duration connectTimeout, Duration readTimeout, int maxBytes) throws Exception;
}
