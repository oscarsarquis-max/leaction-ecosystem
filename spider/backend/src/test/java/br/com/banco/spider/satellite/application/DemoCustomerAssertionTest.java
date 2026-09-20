package br.com.banco.spider.satellite.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.time.Instant;
import org.junit.jupiter.api.Test;

class DemoCustomerAssertionTest {

  private static final String SECRET = "test-assertion-secret";

  @Test
  void verifiesRegisteredSyntheticSubjectForTheAuthorizedSatellite() {
    Instant issued = Instant.now();
    String token = DemoCustomerAssertion.issue(SECRET, "spiderbank", "cust-demo-ok", issued, issued.plusSeconds(600));
    DemoCustomerAssertion.Verified verified = DemoCustomerAssertion.verify(SECRET, "spiderbank", token);
    assertEquals("cust-demo-ok", verified.subjectRef());
  }

  @Test
  void rejectsExpiredWrongSatelliteUnregisteredOrTamperedAssertions() {
    Instant issued = Instant.now();
    String token = DemoCustomerAssertion.issue(SECRET, "spiderbank", "cust-demo-ok", issued, issued.plusSeconds(600));
    assertNull(DemoCustomerAssertion.verify(SECRET, "segsense", token));
    assertNull(
        DemoCustomerAssertion.verify(
            SECRET,
            "spiderbank",
            DemoCustomerAssertion.issue(SECRET, "spiderbank", "cust-demo-ok", issued.minusSeconds(1200), issued.minusSeconds(60))));
    assertNull(DemoCustomerAssertion.verify(SECRET, "spiderbank", token + "00"));
    assertNull(DemoCustomerAssertion.verify("other-assertion-secret", "spiderbank", token));
    assertThrows(
        IllegalArgumentException.class,
        () -> DemoCustomerAssertion.issue(SECRET, "spiderbank", "cust-real-person", issued, issued.plusSeconds(60)));
  }
}
