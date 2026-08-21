package br.com.banco.spider.execution.fingerprint;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

import br.com.banco.spider.canonical.contract.CanonicalPayload;
import br.com.banco.spider.execution.route.CanonicalRouteFixtures;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;

class Sha256CanonicalRequestFingerprintTest {

  private final Sha256CanonicalRequestFingerprint port =
      new Sha256CanonicalRequestFingerprint(new ObjectMapper());
  private final Sha256IdempotencyKeyHash keyHash = new Sha256IdempotencyKeyHash();

  @Test
  void ignoresExecutionIdTimestampAndTrace() {
    var a = CanonicalRouteFixtures.request("exec-A", "k1");
    var b = CanonicalRouteFixtures.request("exec-B", "k1");
    assertEquals(port.fingerprint(a).digest(), port.fingerprint(b).digest());
  }

  @Test
  void changesWithCanonicalData() {
    ObjectMapper mapper = new ObjectMapper();
    ObjectNode d1 = mapper.createObjectNode().put("x", 1);
    ObjectNode d2 = mapper.createObjectNode().put("x", 2);
    var base = CanonicalRouteFixtures.request("e1", "k");
    var r1 =
        br.com.banco.spider.canonical.contract.CanonicalExecutionRequest.builder()
            .contract(base.contract())
            .execution(base.execution())
            .contextRef(base.contextRef())
            .origin(base.origin())
            .trace(base.trace())
            .target(base.target())
            .payload(CanonicalPayload.of(d1))
            .callbackRef(base.callbackRef())
            .build();
    var r2 =
        br.com.banco.spider.canonical.contract.CanonicalExecutionRequest.builder()
            .contract(base.contract())
            .execution(base.execution())
            .contextRef(base.contextRef())
            .origin(base.origin())
            .trace(base.trace())
            .target(base.target())
            .payload(CanonicalPayload.of(d2))
            .callbackRef(base.callbackRef())
            .build();
    assertNotEquals(port.fingerprint(r1).digest(), port.fingerprint(r2).digest());
  }

  @Test
  void stableForEquivalentPropertyOrder() {
    ObjectMapper mapper = new ObjectMapper();
    ObjectNode a = mapper.createObjectNode();
    a.put("b", 2);
    a.put("a", 1);
    ObjectNode b = mapper.createObjectNode();
    b.put("a", 1);
    b.put("b", 2);
    var base = CanonicalRouteFixtures.request("e1", "k");
    var r1 =
        br.com.banco.spider.canonical.contract.CanonicalExecutionRequest.builder()
            .contract(base.contract())
            .execution(base.execution())
            .contextRef(base.contextRef())
            .origin(base.origin())
            .trace(base.trace())
            .target(base.target())
            .payload(CanonicalPayload.of(a))
            .callbackRef(base.callbackRef())
            .build();
    var r2 =
        br.com.banco.spider.canonical.contract.CanonicalExecutionRequest.builder()
            .contract(base.contract())
            .execution(base.execution())
            .contextRef(base.contextRef())
            .origin(base.origin())
            .trace(base.trace())
            .target(base.target())
            .payload(CanonicalPayload.of(b))
            .callbackRef(base.callbackRef())
            .build();
    assertEquals(port.fingerprint(r1).digest(), port.fingerprint(r2).digest());
  }

  @Test
  void keyHashNeverEqualsPlainKey() {
    String key = "plain-secret-key";
    String hash = keyHash.hash(key);
    assertFalse(hash.equalsIgnoreCase(key));
    assertEquals(64, hash.length());
  }
}
