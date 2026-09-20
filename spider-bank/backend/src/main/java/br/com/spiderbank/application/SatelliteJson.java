package br.com.spiderbank.application;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** JDK JSON for the SAT-003 slice. Avoids Jackson 2 packages removed in Spring Boot 4. */
public final class SatelliteJson {

  private SatelliteJson() {}

  public static String write(Map<String, Object> value) {
    StringBuilder out = new StringBuilder();
    writeValue(out, value);
    return out.toString();
  }

  @SuppressWarnings("unchecked")
  public static Map<String, Object> readObject(String json) {
    Object parsed = new Parser(json == null ? "" : json).parseValue();
    if (!(parsed instanceof Map<?, ?> map)) {
      throw new IllegalArgumentException("JSON object expected");
    }
    return (Map<String, Object>) map;
  }

  private static void writeValue(StringBuilder out, Object value) {
    if (value == null) {
      out.append("null");
      return;
    }
    if (value instanceof String text) {
      writeString(out, text);
      return;
    }
    if (value instanceof Boolean || value instanceof Number) {
      out.append(value);
      return;
    }
    if (value instanceof Map<?, ?> map) {
      out.append('{');
      boolean first = true;
      for (Map.Entry<?, ?> entry : map.entrySet()) {
        if (!first) {
          out.append(',');
        }
        first = false;
        writeString(out, String.valueOf(entry.getKey()));
        out.append(':');
        writeValue(out, entry.getValue());
      }
      out.append('}');
      return;
    }
    if (value instanceof Iterable<?> list) {
      out.append('[');
      boolean first = true;
      for (Object item : list) {
        if (!first) {
          out.append(',');
        }
        first = false;
        writeValue(out, item);
      }
      out.append(']');
      return;
    }
    writeString(out, String.valueOf(value));
  }

  private static void writeString(StringBuilder out, String text) {
    out.append('"');
    for (int i = 0; i < text.length(); i++) {
      char c = text.charAt(i);
      switch (c) {
        case '"' -> out.append("\\\"");
        case '\\' -> out.append("\\\\");
        case '\n' -> out.append("\\n");
        case '\r' -> out.append("\\r");
        case '\t' -> out.append("\\t");
        default -> {
          if (c < 0x20) {
            out.append(String.format("\\u%04x", (int) c));
          } else {
            out.append(c);
          }
        }
      }
    }
    out.append('"');
  }

  private static final class Parser {
    private final String json;
    private int index;

    Parser(String json) {
      this.json = json;
    }

    Object parseValue() {
      skipWs();
      if (index >= json.length()) {
        throw new IllegalArgumentException("empty JSON");
      }
      char c = json.charAt(index);
      if (c == '{') {
        return parseObject();
      }
      if (c == '[') {
        return parseArray();
      }
      if (c == '"') {
        return parseString();
      }
      if (c == 't' || c == 'f') {
        return parseBoolean();
      }
      if (c == 'n') {
        consume("null");
        return null;
      }
      return parseNumber();
    }

    private Map<String, Object> parseObject() {
      consume('{');
      Map<String, Object> map = new LinkedHashMap<>();
      skipWs();
      if (peek('}')) {
        consume('}');
        return map;
      }
      while (true) {
        skipWs();
        String key = parseString();
        skipWs();
        consume(':');
        map.put(key, parseValue());
        skipWs();
        if (peek('}')) {
          consume('}');
          return map;
        }
        consume(',');
      }
    }

    private List<Object> parseArray() {
      consume('[');
      List<Object> list = new ArrayList<>();
      skipWs();
      if (peek(']')) {
        consume(']');
        return list;
      }
      while (true) {
        list.add(parseValue());
        skipWs();
        if (peek(']')) {
          consume(']');
          return list;
        }
        consume(',');
      }
    }

    private String parseString() {
      consume('"');
      StringBuilder out = new StringBuilder();
      while (index < json.length()) {
        char c = json.charAt(index++);
        if (c == '"') {
          return out.toString();
        }
        if (c == '\\') {
          if (index >= json.length()) {
            throw new IllegalArgumentException("unterminated escape");
          }
          char escaped = json.charAt(index++);
          out.append(
              switch (escaped) {
                case '"' -> '"';
                case '\\' -> '\\';
                case '/' -> '/';
                case 'n' -> '\n';
                case 'r' -> '\r';
                case 't' -> '\t';
                case 'u' -> (char) Integer.parseInt(json.substring(index, index + 4), 16);
                default -> escaped;
              });
          if (escaped == 'u') {
            index += 4;
          }
          continue;
        }
        out.append(c);
      }
      throw new IllegalArgumentException("unterminated string");
    }

    private boolean parseBoolean() {
      if (peek('t')) {
        consume("true");
        return true;
      }
      consume("false");
      return false;
    }

    private Number parseNumber() {
      int start = index;
      if (peek('-')) {
        index++;
      }
      while (index < json.length() && isNumberChar(json.charAt(index))) {
        index++;
      }
      String raw = json.substring(start, index);
      if (raw.contains(".") || raw.contains("e") || raw.contains("E")) {
        return Double.parseDouble(raw);
      }
      return Long.parseLong(raw);
    }

    private static boolean isNumberChar(char c) {
      return (c >= '0' && c <= '9') || c == '.' || c == 'e' || c == 'E' || c == '+' || c == '-';
    }

    private void consume(char expected) {
      skipWs();
      if (index >= json.length() || json.charAt(index) != expected) {
        throw new IllegalArgumentException("expected " + expected);
      }
      index++;
    }

    private void consume(String token) {
      skipWs();
      if (!json.startsWith(token, index)) {
        throw new IllegalArgumentException("expected " + token);
      }
      index += token.length();
    }

    private boolean peek(char expected) {
      skipWs();
      return index < json.length() && json.charAt(index) == expected;
    }

    private void skipWs() {
      while (index < json.length()) {
        char c = json.charAt(index);
        if (c != ' ' && c != '\n' && c != '\r' && c != '\t') {
          return;
        }
        index++;
      }
    }
  }
}
