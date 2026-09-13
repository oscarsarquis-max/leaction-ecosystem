package br.com.segsense.inbound.http.link;

import org.springframework.http.HttpHeaders;

public final class NonStoreHeaders {

  private NonStoreHeaders() {}

  public static HttpHeaders of() {
    HttpHeaders headers = new HttpHeaders();
    headers.setCacheControl("no-store");
    headers.setPragma("no-cache");
    headers.add("Referrer-Policy", "no-referrer");
    headers.add("X-Content-Type-Options", "nosniff");
    return headers;
  }
}
