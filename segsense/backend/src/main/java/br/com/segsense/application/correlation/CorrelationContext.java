package br.com.segsense.application.correlation;

import java.util.UUID;

public final class CorrelationContext {

  public static final String MDC_KEY = "correlationId";
  public static final String HTTP_HEADER = "X-Correlation-ID";

  private static final ThreadLocal<UUID> CURRENT = new ThreadLocal<>();

  private CorrelationContext() {}

  public static void set(UUID correlationId) {
    CURRENT.set(correlationId);
  }

  public static UUID current() {
    return CURRENT.get();
  }

  public static void clear() {
    CURRENT.remove();
  }
}
