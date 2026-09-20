package br.com.spiderbank.application;

import java.util.Map;

public interface SpiderDecisionGateway {

  Result submit(Command command);

  record Command(
      String correlationId,
      String idempotencyKey,
      String messageId,
      String declaredAt,
      Map<String, String> attributes,
      Map<String, Object> extensions) {

    public Command(
        String correlationId,
        String idempotencyKey,
        String messageId,
        String declaredAt,
        Map<String, String> attributes) {
      this(correlationId, idempotencyKey, messageId, declaredAt, attributes, Map.of());
    }
  }

  record Result(Kind kind, int httpStatus, String errorCode, String message, Map<String, Object> body) {
    public static Result ok(Map<String, Object> body) {
      return new Result(Kind.OK, 200, null, null, body);
    }

    public static Result spiderUnavailable() {
      return new Result(
          Kind.SPIDER_UNAVAILABLE,
          503,
          "SPIDER_UNAVAILABLE",
          "A Spider está indisponível neste momento. Isso não é recusa de crédito.",
          Map.of());
    }

    public static Result integrationFailure(String message) {
      return new Result(Kind.INTEGRATION_FAILURE, 502, "INTEGRATION_FAILURE", message, Map.of());
    }
  }

  enum Kind {
    OK,
    CLIENT_ERROR,
    SPIDER_UNAVAILABLE,
    INTEGRATION_FAILURE
  }
}
