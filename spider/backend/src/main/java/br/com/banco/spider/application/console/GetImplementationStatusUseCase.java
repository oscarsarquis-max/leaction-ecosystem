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
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

@Service
public class GetImplementationStatusUseCase {

  private final ImplementationManifestLoader loader;
  private final OperationalConsoleProperties consoleProps;
  private final CanonicalHttpProperties canonicalHttp;
  private final Environment environment;
  private final String appVersion;

  public GetImplementationStatusUseCase(
      ImplementationManifestLoader loader,
      OperationalConsoleProperties consoleProps,
      CanonicalHttpProperties canonicalHttp,
      Environment environment,
      @Value("${spring.application.name:spider}") String appName) {
    this.loader = loader;
    this.consoleProps = consoleProps;
    this.canonicalHttp = canonicalHttp;
    this.environment = environment;
    this.appVersion = appName;
  }

  public Mono<Map<String, Object>> execute() {
    return Mono.fromCallable(this::build).subscribeOn(Schedulers.boundedElastic());
  }

  private Map<String, Object> build() {
    SpiderImplementationManifest manifest = loader.getManifest();
    Map<String, Object> out = new LinkedHashMap<>();
    out.put("runtimeVersion", appVersion + "@" + manifest.productVersion());
    out.put("productVersion", manifest.productVersion());
    out.put("manifestVersion", manifest.manifestVersion());
    out.put("currentPrompt", manifest.currentPrompt());
    out.put("currentGroup", manifest.currentGroup());
    out.put("lastVerifiedAt", manifest.lastVerifiedAt());
    out.put("baseline", manifest.baseline());
    out.put("capabilities", manifest.capabilities());
    out.put("externalBoundaries", manifest.externalBoundaries());
    out.put("governanceMode", environment.getProperty("spider.governance.mode", "STATIC"));
    out.put("effectiveFlags", redactedFlags());
    out.put("mockRealBoundary", "MOCK_ONLY");
    out.put("groups", groupSummary(manifest.capabilities()));
    return out;
  }

  private Map<String, Object> redactedFlags() {
    Map<String, Object> flags = new LinkedHashMap<>();
    flags.put("spider.console.enabled", consoleProps.isEnabled());
    flags.put("spider.console.http.enabled", consoleProps.getHttp().isEnabled());
    flags.put("spider.console.local-demo.enabled", consoleProps.getLocalDemo().isEnabled());
    flags.put("spider.console.safe-projections.enabled", consoleProps.getSafeProjections().isEnabled());
    flags.put("spider.canonical.http.enabled", canonicalHttp.isEnabled());
    flags.put("spider.canonical.http.status-query-enabled", canonicalHttp.isStatusQueryEnabled());
    flags.put("spider.adapter.mock.enabled", environment.getProperty("spider.adapter.mock.enabled", "true"));
    // never include secrets/jwt/datasource passwords
    return flags;
  }

  private static List<Map<String, Object>> groupSummary(List<ImplementationCapability> caps) {
    List<String> officialOrder =
        List.of(
            "GROUP_A_VISIBILITY_OBSERVABILITY",
            "GROUP_B_RUNTIME_OPERATIONS",
            "GROUP_C_PLATFORM_READINESS",
            "GROUP_D_REAL_INTEGRATION");
    Map<String, int[]> counts = new LinkedHashMap<>();
    // [total, verified, planned]
    for (ImplementationCapability c : caps) {
      counts.computeIfAbsent(c.groupCode(), k -> new int[] {0, 0, 0});
      int[] arr = counts.get(c.groupCode());
      arr[0]++;
      if ("VERIFIED".equals(c.status()) || "IMPLEMENTED".equals(c.status())) {
        arr[1]++;
      }
      if ("PLANNED".equals(c.status())) {
        arr[2]++;
      }
    }
    List<Map<String, Object>> groups = new ArrayList<>();
    for (String code : officialOrder) {
      if (!counts.containsKey(code)) {
        continue;
      }
      int[] arr = counts.get(code);
      Map<String, Object> g = new LinkedHashMap<>();
      g.put("groupCode", code);
      g.put("total", arr[0]);
      g.put("verified", arr[1]);
      g.put("planned", arr[2]);
      g.put("done", arr[1]);
      g.put("denominator", arr[0]);
      g.put("journey", true);
      groups.add(g);
      counts.remove(code);
    }
    counts.forEach(
        (code, arr) -> {
          Map<String, Object> g = new LinkedHashMap<>();
          g.put("groupCode", code);
          g.put("total", arr[0]);
          g.put("verified", arr[1]);
          g.put("planned", arr[2]);
          g.put("done", arr[1]);
          g.put("denominator", arr[0]);
          g.put("journey", false);
          g.put("historical", true);
          groups.add(g);
        });
    return groups;
  }
}
