package br.com.banco.spider.application.console;

import br.com.banco.spider.config.CanonicalHttpProperties;
import br.com.banco.spider.config.OperationalConsoleProperties;
import br.com.banco.spider.implementation.ImplementationCapability;
import br.com.banco.spider.implementation.ImplementationManifestLoader;
import br.com.banco.spider.implementation.SpiderImplementationManifest;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

@Service
public class PresentationReadinessUseCase {

  public static final List<String> DEMO_SCENARIOS =
      List.of(
          "SUCCESS_MULTI_STEP",
          "RETRY_THEN_SUCCESS",
          "WAIT_SIGNAL_RESUME",
          "CALLBACK_RECONCILIATION");

  private final ImplementationManifestLoader loader;
  private final OperationalConsoleProperties consoleProps;
  private final CanonicalHttpProperties canonicalHttp;
  private final Environment environment;

  public PresentationReadinessUseCase(
      ImplementationManifestLoader loader,
      OperationalConsoleProperties consoleProps,
      CanonicalHttpProperties canonicalHttp,
      Environment environment) {
    this.loader = loader;
    this.consoleProps = consoleProps;
    this.canonicalHttp = canonicalHttp;
    this.environment = environment;
  }

  public Mono<PresentationReadinessView> execute() {
    return Mono.fromCallable(this::evaluate).subscribeOn(Schedulers.boundedElastic());
  }

  private PresentationReadinessView evaluate() {
    List<Check> checks = new ArrayList<>();
    SpiderImplementationManifest manifest = null;
    String manifestStatus = "INVALID";
    try {
      manifest = loader.getManifest();
      manifestStatus = "VALID";
      checks.add(ok("manifest_valid", "Capability manifest loaded and valid"));
    } catch (Exception e) {
      checks.add(fail("manifest_valid", "Manifest invalid or unloadable"));
    }

    checks.add(
        bool(
            "console_api_enabled",
            consoleProps.isEnabled() && consoleProps.getHttp().isEnabled(),
            "Console HTTP enabled",
            "Console HTTP disabled"));
    checks.add(
        bool(
            "canonical_submit_enabled",
            canonicalHttp.isEnabled(),
            "Canonical submit enabled",
            "Canonical submit disabled"));
    checks.add(
        bool(
            "canonical_status_enabled",
            canonicalHttp.isStatusQueryEnabled(),
            "Canonical status query enabled",
            "Canonical status query disabled"));

    String persistence = environment.getProperty("spider.canonical.persistence.mode", "memory");
    checks.add(
        bool(
            "persistence_available",
            "memory".equalsIgnoreCase(persistence) || "jpa".equalsIgnoreCase(persistence),
            "Persistence mode available (" + persistence + ")",
            "Persistence unavailable"));

    boolean mockAdapter =
        Boolean.parseBoolean(environment.getProperty("spider.adapter.mock.enabled", "true"));
    checks.add(
        bool(
            "mock_bootstrap_ready",
            mockAdapter,
            "Mock adapter enabled",
            "Mock adapter not enabled"));

    checks.add(
        bool(
            "active_mock_bundle",
            mockAdapter,
            "Active Mock bundle boundary assumed for local-demo",
            "No Mock bundle"));

    checks.add(
        bool(
            "mock_scenarios_available",
            true,
            "Demo scenarios catalog present",
            "Demo scenarios missing"));

    boolean integrityMock =
        !Boolean.parseBoolean(environment.getProperty("spider.security.integrity.enabled", "false"))
            || Boolean.parseBoolean(
                environment.getProperty("spider.security.mock-key-provider.enabled", "false"));
    checks.add(
        bool(
            "integrity_dp_mock_coherent",
            integrityMock,
            "Integrity/Data Protection Mock posture coherent",
            "Integrity requires non-Mock key material"));

    boolean realAdapter =
        Boolean.parseBoolean(environment.getProperty("spider.adapter.real.enabled", "false"));
    checks.add(
        bool(
            "no_real_adapter",
            !realAdapter && mockAdapter,
            "No real Adapter active (Mock-only)",
            "Real Adapter flag detected"));

    checks.add(
        bool(
            "version_compatible",
            manifest != null && "0.15.0".equals(manifest.productVersion()),
            "Frontend/backend productVersion compatible (0.15.0)",
            "Version mismatch"));

    List<String> failing =
        checks.stream().filter(c -> !c.passed()).map(Check::code).toList();
    boolean ready = failing.isEmpty();

    List<String> scenarios = new ArrayList<>(DEMO_SCENARIOS);
    if (manifest != null) {
      ImplementationCapability cap15 =
          manifest.capabilities().stream()
              .filter(c -> "CAP-015".equals(c.capabilityCode()))
              .findFirst()
              .orElse(null);
      if (cap15 == null) {
        ready = false;
        failing = new ArrayList<>(failing);
        failing.add("cap_015_missing");
      }
    }

    return new PresentationReadinessView(
        ready,
        "spider@0.15.0",
        manifestStatus,
        checks,
        scenarios,
        failing,
        Instant.now().toString(),
        "MOCK_ONLY");
  }

  private static Check ok(String code, String message) {
    return new Check(code, true, message);
  }

  private static Check fail(String code, String message) {
    return new Check(code, false, message);
  }

  private static Check bool(String code, boolean passed, String okMsg, String failMsg) {
    return new Check(code, passed, passed ? okMsg : failMsg);
  }

  public record Check(String code, boolean passed, String message) {}

  public record PresentationReadinessView(
      boolean ready,
      String runtimeVersion,
      String manifestStatus,
      List<Check> checks,
      List<String> availableScenarios,
      List<String> failingChecks,
      String lastVerifiedAt,
      String boundary) {}
}
