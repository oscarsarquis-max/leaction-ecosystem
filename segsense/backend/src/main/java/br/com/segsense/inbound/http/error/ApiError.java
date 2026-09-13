package br.com.segsense.inbound.http.error;

import java.time.Instant;

public record ApiError(String code, String message, Instant timestamp, String correlationId) {

  public static ApiError of(String code, String message, String correlationId) {
    return new ApiError(code, message, Instant.now(), correlationId);
  }
}
