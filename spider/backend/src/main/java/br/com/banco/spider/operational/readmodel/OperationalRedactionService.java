package br.com.banco.spider.operational.readmodel;

import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.stereotype.Service;

@Service
public class OperationalRedactionService {

  private static final Set<String> SENSITIVE =
      Set.of(
          "token",
          "secret",
          "password",
          "authorization",
          "mac",
          "nonce",
          "ciphertext",
          "iv",
          "key",
          "jwt",
          "continuationtoken",
          "idempotencykey",
          "fingerprint");

  public record RedactionResult(Map<String, Object> projection, int redactedFieldsCount) {}

  public RedactionResult redact(Map<String, Object> input, int maxDepth, int maxString) {
    AtomicInteger count = new AtomicInteger();
    Object cleaned = walk(input, 0, maxDepth, maxString, count);
    @SuppressWarnings("unchecked")
    Map<String, Object> map =
        cleaned instanceof Map<?, ?> m
            ? (Map<String, Object>) m
            : Map.of("value", cleaned == null ? "" : cleaned);
    return new RedactionResult(map, count.get());
  }

  private Object walk(Object node, int depth, int maxDepth, int maxString, AtomicInteger count) {
    if (node == null) {
      return null;
    }
    if (depth > maxDepth) {
      count.incrementAndGet();
      return "[TRUNCATED_DEPTH]";
    }
    if (node instanceof Map<?, ?> map) {
      Map<String, Object> out = new LinkedHashMap<>();
      for (Map.Entry<?, ?> e : map.entrySet()) {
        String key = String.valueOf(e.getKey());
        if (isSensitiveKey(key)) {
          count.incrementAndGet();
          continue;
        }
        out.put(key, walk(e.getValue(), depth + 1, maxDepth, maxString, count));
      }
      return out;
    }
    if (node instanceof Iterable<?> it) {
      java.util.List<Object> list = new java.util.ArrayList<>();
      int i = 0;
      Iterator<?> iter = it.iterator();
      while (iter.hasNext() && i < 32) {
        list.add(walk(iter.next(), depth + 1, maxDepth, maxString, count));
        i++;
      }
      if (iter.hasNext()) {
        count.incrementAndGet();
        list.add("[TRUNCATED_ARRAY]");
      }
      return list;
    }
    if (node instanceof String s) {
      if (s.length() > maxString) {
        count.incrementAndGet();
        return s.substring(0, maxString) + "…[TRUNCATED]";
      }
      return s;
    }
    return node;
  }

  private static boolean isSensitiveKey(String key) {
    String k = key.toLowerCase(Locale.ROOT).replace("_", "").replace("-", "");
    for (String s : SENSITIVE) {
      if (k.contains(s)) {
        return true;
      }
    }
    return false;
  }
}
