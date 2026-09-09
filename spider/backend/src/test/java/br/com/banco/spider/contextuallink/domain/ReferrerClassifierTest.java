package br.com.banco.spider.contextuallink.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import org.junit.jupiter.api.Test;

class ReferrerClassifierTest {

  @Test
  void fullReferrerKeepsPath() {
    var result = ReferrerClassifier.classify("http://127.0.0.1:5180/partner/agro-hoje/");
    assertEquals(ReferrerAvailability.FULL_REFERRER_AVAILABLE, result.availability());
    assertEquals("http://127.0.0.1:5180", result.origin());
  }

  @Test
  void originOnlyWhenPathIsRoot() {
    var result = ReferrerClassifier.classify("http://127.0.0.1:5180/");
    assertEquals(ReferrerAvailability.ORIGIN_ONLY, result.availability());
  }

  @Test
  void missingReferrerIsUnavailable() {
    var result = ReferrerClassifier.classify(" ");
    assertEquals(ReferrerAvailability.REFERRER_UNAVAILABLE, result.availability());
    assertEquals("", result.referrer());
    assertNull(result.fullUri());
  }
}
