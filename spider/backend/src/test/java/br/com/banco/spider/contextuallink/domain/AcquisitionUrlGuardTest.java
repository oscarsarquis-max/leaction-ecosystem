package br.com.banco.spider.contextuallink.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.List;
import org.junit.jupiter.api.Test;

class AcquisitionUrlGuardTest {

  private final AcquisitionUrlGuard guard =
      new AcquisitionUrlGuard(
          List.of("http://127.0.0.1:5180", "http://127.0.0.1:8080"),
          List.of("/partner/", "/demo/partner/"));

  @Test
  void allowsDemoPartnerPage() {
    assertEquals(
        "/partner/agro-hoje/",
        guard.validate("http://127.0.0.1:5180/partner/agro-hoje/").getPath());
  }

  @Test
  void blocksFileScheme() {
    var ex =
        assertThrows(
            AcquisitionUrlGuard.BlockedAcquisitionException.class,
            () -> guard.validate("file:///etc/passwd"));
    assertEquals("scheme_not_allowed", ex.getMessage());
  }

  @Test
  void blocksMetadataHost() {
    var ex =
        assertThrows(
            AcquisitionUrlGuard.BlockedAcquisitionException.class,
            () -> guard.validate("http://169.254.169.254/latest/meta-data"));
    assertEquals("metadata_blocked", ex.getMessage());
  }

  @Test
  void blocksPrivateNetworkNotAllowlisted() {
    var ex =
        assertThrows(
            AcquisitionUrlGuard.BlockedAcquisitionException.class,
            () -> guard.validate("http://192.168.0.10/partner/agro-hoje/"));
    assertEquals("origin_not_allowlisted", ex.getMessage());
  }

  @Test
  void blocksActuatorOnLoopback() {
    var ex =
        assertThrows(
            AcquisitionUrlGuard.BlockedAcquisitionException.class,
            () -> guard.validate("http://127.0.0.1:8080/actuator/health"));
    assertEquals("path_not_allowlisted", ex.getMessage());
  }

  @Test
  void blocksRedirectOffAllowlist() {
    var current = guard.validate("http://127.0.0.1:5180/partner/agro-hoje/");
    var ex =
        assertThrows(
            AcquisitionUrlGuard.BlockedAcquisitionException.class,
            () -> guard.validateRedirect(current, "http://evil.example/steal"));
    assertEquals("origin_not_allowlisted", ex.getMessage());
  }
}
