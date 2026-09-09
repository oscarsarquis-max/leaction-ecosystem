package br.com.banco.spider.contextuallink.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class ContentFingerprintTest {

  @Test
  void sameCanonicalContentProducesSameHash() {
    String a = ContentFingerprint.sha256("http://x/a", "Título", "desc", "Texto  um");
    String b = ContentFingerprint.sha256("http://x/a", "título", "DESC", "texto um");
    assertEquals(a, b);
    assertTrue(a.startsWith("sha256:"));
    assertEquals(71, a.length());
  }

  @Test
  void differentBodyChangesHash() {
    String a = ContentFingerprint.sha256("u", "t", "d", "a");
    String b = ContentFingerprint.sha256("u", "t", "d", "b");
    assertNotEquals(a, b);
  }
}
