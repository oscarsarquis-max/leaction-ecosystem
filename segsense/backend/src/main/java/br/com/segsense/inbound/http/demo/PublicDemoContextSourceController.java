package br.com.segsense.inbound.http.demo;

import br.com.segsense.application.demo.DemoContextUrlGuard;
import br.com.segsense.application.demo.DemoGovernedUrlSettings;
import br.com.segsense.application.demo.GovernedDemoSource;
import br.com.segsense.application.demo.GovernedDemoSourceRegistry;
import br.com.segsense.inbound.http.link.NonStoreHeaders;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@Profile({"local", "test"})
@ConditionalOnProperty(name = "segsense.demo.protection-journey.enabled", havingValue = "true")
@RequestMapping("/api/v1/public/demo/context-sources")
public class PublicDemoContextSourceController {

  private final DemoGovernedUrlSettings governedUrls;
  private final String publicBaseUrl;

  public PublicDemoContextSourceController(
      DemoGovernedUrlSettings governedUrls,
      @Value("${segsense.public.base-url:http://127.0.0.1:5178}") String publicBaseUrl) {
    this.governedUrls = governedUrls;
    this.publicBaseUrl = publicBaseUrl.endsWith("/") ? publicBaseUrl.substring(0, publicBaseUrl.length() - 1) : publicBaseUrl;
  }

  @GetMapping
  public ResponseEntity<List<Map<String, Object>>> list() {
    List<Map<String, Object>> items =
        GovernedDemoSourceRegistry.listPublic().stream().map(this::summary).toList();
    return ResponseEntity.ok().headers(NonStoreHeaders.of()).body(items);
  }

  @PostMapping("/resolve")
  public ResponseEntity<Map<String, Object>> resolve(@RequestBody(required = false) Map<String, String> body) {
    String raw = body == null ? null : body.get("url");
    DemoContextUrlGuard.Accepted accepted = DemoContextUrlGuard.accept(raw, governedUrls.allowedPorts());
    String slug = DemoContextUrlGuard.slugOf(accepted.path()).orElseThrow();
    GovernedDemoSource source = GovernedDemoSourceRegistry.requireLive(slug);
    Map<String, Object> payload = summary(source);
    payload.put("path", accepted.path());
    payload.put("url", accepted.referenceUrl());
    payload.put("authorizedExcerpt", source.authorizedExcerpt());
    payload.put("elements", source.attributes());
    return ResponseEntity.ok().headers(NonStoreHeaders.of()).body(payload);
  }

  private Map<String, Object> summary(GovernedDemoSource source) {
    Map<String, Object> map = new LinkedHashMap<>();
    map.put("id", source.id());
    map.put("slug", source.slug());
    map.put("title", source.title());
    map.put("sourceLabel", source.sourceLabel());
    map.put("version", source.version());
    map.put("capturedAt", source.capturedAt());
    map.put("revoked", source.revoked());
    map.put("url", publicBaseUrl + "/demonstracao/fontes/" + source.slug());
    return map;
  }
}
