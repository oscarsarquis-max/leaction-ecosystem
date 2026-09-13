package br.com.segsense.inbound.http.error;

import java.nio.charset.StandardCharsets;

public final class ApiErrorBody {

  private ApiErrorBody() {}

  public static byte[] utf8(ApiError error) {
    String correlationJson =
        error.correlationId() == null ? "null" : jsonString(error.correlationId());
    String json =
        "{\"code\":"
            + jsonString(error.code())
            + ",\"message\":"
            + jsonString(error.message())
            + ",\"timestamp\":"
            + jsonString(error.timestamp().toString())
            + ",\"correlationId\":"
            + correlationJson
            + "}";
    return json.getBytes(StandardCharsets.UTF_8);
  }

  private static String jsonString(String value) {
    return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
  }
}
