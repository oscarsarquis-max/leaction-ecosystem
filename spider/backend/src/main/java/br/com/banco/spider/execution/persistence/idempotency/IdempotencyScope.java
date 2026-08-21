package br.com.banco.spider.execution.persistence.idempotency;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Objects;

/**
 * Escopo idempotente — sem executionId.
 * scopeHash = sha256(originator|capability|operation|contractMajor).
 */
public record IdempotencyScope(
    String originatorId, String capabilityCode, String operationCode, String contractMajorVersion) {

  public IdempotencyScope {
    originatorId = require("originatorId", originatorId);
    capabilityCode = require("capabilityCode", capabilityCode);
    operationCode = require("operationCode", operationCode);
    contractMajorVersion = require("contractMajorVersion", contractMajorVersion);
  }

  public String scopeHash() {
    String canonical =
        originatorId
            + '|'
            + capabilityCode
            + '|'
            + operationCode
            + '|'
            + contractMajorVersion;
    return sha256Hex(canonical);
  }

  private static String require(String name, String value) {
    Objects.requireNonNull(value, name);
    String t = value.trim();
    if (t.isEmpty()) {
      throw new IllegalArgumentException(name + " must not be blank");
    }
    return t;
  }

  private static String sha256Hex(String value) {
    try {
      MessageDigest md = MessageDigest.getInstance("SHA-256");
      return HexFormat.of().formatHex(md.digest(value.getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException e) {
      throw new IllegalStateException("SHA-256 unavailable", e);
    }
  }
}
