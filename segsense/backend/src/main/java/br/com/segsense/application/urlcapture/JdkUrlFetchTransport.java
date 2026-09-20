package br.com.segsense.application.urlcapture;

import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

final class JdkUrlFetchTransport implements UrlFetchTransport {

  private final HttpClient client;

  JdkUrlFetchTransport(Duration connectTimeout) {
    this.client =
        HttpClient.newBuilder()
            .followRedirects(HttpClient.Redirect.NEVER)
            .connectTimeout(connectTimeout)
            .build();
  }

  @Override
  public Response get(URI uri, Duration connectTimeout, Duration readTimeout, int maxBytes) throws Exception {
    HttpRequest request =
        HttpRequest.newBuilder(uri)
            .timeout(readTimeout)
            .GET()
            .header("User-Agent", "SegSense-URLCapture/1.0")
            .header("Accept", "text/html, application/xhtml+xml, text/plain;q=0.9")
            .header("Accept-Language", "pt-BR,pt;q=0.9")
            .build();
    HttpResponse<InputStream> response = client.send(request, HttpResponse.BodyHandlers.ofInputStream());
    byte[] body = readLimited(response.body(), maxBytes + 1);
    String contentType = response.headers().firstValue("content-type").orElse("");
    String location = response.headers().firstValue("location").orElse(null);
    return new Response(response.statusCode(), contentType, location, body, Map.copyOf(response.headers().map()));
  }

  static byte[] readLimited(InputStream stream, int limit) throws Exception {
    byte[] buffer = new byte[8192];
    List<byte[]> chunks = new ArrayList<>();
    int total = 0;
    int read;
    while ((read = stream.read(buffer)) != -1) {
      byte[] copy = new byte[read];
      System.arraycopy(buffer, 0, copy, 0, read);
      chunks.add(copy);
      total += read;
      if (total > limit) {
        break;
      }
    }
    byte[] all = new byte[Math.min(total, limit)];
    int offset = 0;
    for (byte[] chunk : chunks) {
      int take = Math.min(chunk.length, all.length - offset);
      System.arraycopy(chunk, 0, all, offset, take);
      offset += take;
      if (offset >= all.length) {
        break;
      }
    }
    return all;
  }
}
