package br.com.segsense.application.demo;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import br.com.segsense.domain.demo.DemoProtectionException;
import org.junit.jupiter.api.Test;

class DemoContextUrlGuardTest {

  @Test
  void acceptsLoopbackGovernedPath() {
    assertEquals(
        "/demonstracao/fontes/continuidade-familiar",
        DemoContextUrlGuard.normalizeOrReject("http://127.0.0.1:5178/demonstracao/fontes/continuidade-familiar"));
  }

  @Test
  void acceptsConfiguredIsolatedPort() {
    assertEquals(
        "/demonstracao/fontes/continuidade-familiar",
        DemoContextUrlGuard.accept(
                "http://127.0.0.1:15178/demonstracao/fontes/continuidade-familiar", java.util.Set.of(15178))
            .path());
  }

  @Test
  void rejectsPrivateHost() {
    DemoProtectionException error =
        assertThrows(
            DemoProtectionException.class,
            () -> DemoContextUrlGuard.normalizeOrReject("http://192.168.0.10:5178/demonstracao/fontes/continuidade-familiar"));
    assertEquals("INVALID_CONTEXT_URL", error.code());
  }

  @Test
  void rejectsFileAndMetadata() {
    assertThrows(
        DemoProtectionException.class, () -> DemoContextUrlGuard.normalizeOrReject("file:///etc/passwd"));
    assertThrows(
        DemoProtectionException.class,
        () -> DemoContextUrlGuard.normalizeOrReject("http://127.0.0.1:8095/health"));
    assertThrows(
        DemoProtectionException.class,
        () -> DemoContextUrlGuard.normalizeOrReject("http://169.254.169.254/latest/meta-data"));
  }
}
