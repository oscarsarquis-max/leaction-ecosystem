package br.com.banco.spider.application.security;

import java.time.Instant;
import java.util.Map;
import java.util.Objects;

public record IngressAuthenticationRequest(
    String transportProfile,
    String credentialMaterialRef,
    Map<String, String> requestMetadata,
    String remotePeerRef,
    Instant receivedAt) {

  public IngressAuthenticationRequest {
    Objects.requireNonNull(transportProfile, "transportProfile");
    Objects.requireNonNull(receivedAt, "receivedAt");
    requestMetadata = requestMetadata == null ? Map.of() : Map.copyOf(requestMetadata);
  }
}
