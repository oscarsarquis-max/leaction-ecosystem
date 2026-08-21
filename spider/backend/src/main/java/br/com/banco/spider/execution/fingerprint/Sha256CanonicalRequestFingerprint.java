package br.com.banco.spider.execution.fingerprint;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Iterator;
import java.util.Map;
import java.util.TreeMap;
import org.springframework.stereotype.Component;

/**
 * Fingerprint v1.0 — SHA-256 sobre JSON canônico ordenado.
 * Limitação: sem HMAC; reforço criptográfico adiado (PROMPT-004+).
 */
@Component
public class Sha256CanonicalRequestFingerprint implements CanonicalRequestFingerprintPort {

  public static final String VERSION = "1.0";

  private final ObjectMapper sortedMapper;

  public Sha256CanonicalRequestFingerprint(ObjectMapper objectMapper) {
    this.sortedMapper = objectMapper.copy().configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);
  }

  @Override
  public FingerprintResult fingerprint(CanonicalExecutionRequest request) {
    try {
      ObjectNode root = sortedMapper.createObjectNode();
      root.put("fingerprintVersion", VERSION);
      root.put("contractMajor", major(request.contract().contractVersion()));
      root.put("originatorId", request.origin().originatorId());
      root.put("channel", request.origin().channel());
      root.put("capability", request.target().capability());
      root.put("operation", request.target().operation());
      root.put("contextId", request.contextRef().contextId());
      root.put("journeyId", request.contextRef().journeyId());
      root.put("intentId", request.contextRef().intentId());
      root.put("capabilityId", request.contextRef().capabilityId());
      root.put("productServiceId", request.contextRef().productServiceId());
      if (request.callbackRef() != null) {
        root.put("callbackRef", request.callbackRef().ref() + "@" + request.callbackRef().version());
      }
      root.set("canonicalData", sortNode(request.payload() != null ? request.payload().canonicalData() : null));
      String json = sortedMapper.writeValueAsString(root);
      return new FingerprintResult(sha256(json), VERSION);
    } catch (Exception e) {
      throw new IllegalStateException("Failed to compute request fingerprint", e);
    }
  }

  private JsonNode sortNode(JsonNode node) {
    if (node == null || node.isNull()) {
      return sortedMapper.nullNode();
    }
    if (node.isObject()) {
      ObjectNode out = sortedMapper.createObjectNode();
      TreeMap<String, JsonNode> sorted = new TreeMap<>();
      Iterator<Map.Entry<String, JsonNode>> fields = node.fields();
      while (fields.hasNext()) {
        Map.Entry<String, JsonNode> e = fields.next();
        sorted.put(e.getKey(), sortNode(e.getValue()));
      }
      sorted.forEach(out::set);
      return out;
    }
    if (node.isArray()) {
      var arr = sortedMapper.createArrayNode();
      node.forEach(n -> arr.add(sortNode(n)));
      return arr;
    }
    return node;
  }

  private static String major(String version) {
    if (version == null || version.isBlank()) {
      return "0";
    }
    int dot = version.indexOf('.');
    return dot < 0 ? version : version.substring(0, dot);
  }

  private static String sha256(String value) {
    try {
      MessageDigest md = MessageDigest.getInstance("SHA-256");
      return HexFormat.of().formatHex(md.digest(value.getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException e) {
      throw new IllegalStateException(e);
    }
  }
}
