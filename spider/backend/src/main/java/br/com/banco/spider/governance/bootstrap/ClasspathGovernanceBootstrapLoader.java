package br.com.banco.spider.governance.bootstrap;

import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import br.com.banco.spider.governance.AdapterKind;
import br.com.banco.spider.governance.BindingDescriptor;
import br.com.banco.spider.governance.GovernanceArtifact;
import br.com.banco.spider.governance.GovernanceArtifactCodecRegistry;
import br.com.banco.spider.governance.GovernanceArtifactType;
import br.com.banco.spider.governance.GovernanceBundle;
import br.com.banco.spider.governance.GovernanceControlPlaneService;
import br.com.banco.spider.governance.GovernanceLifecycleState;
import br.com.banco.spider.governance.GovernanceScope;
import br.com.banco.spider.execution.route.RouteDefinition;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

/**
 * Bootstrap classpath fechado — somente prefixo allowlist; passa pelos use cases do Control Plane.
 */
@Component
@ConditionalOnProperty(name = "spider.governance.bootstrap.enabled", havingValue = "true")
public class ClasspathGovernanceBootstrapLoader implements GovernanceBootstrapLoaderPort {

  private static final Logger log = LoggerFactory.getLogger(ClasspathGovernanceBootstrapLoader.class);

  private final GovernanceControlPlaneService cps;
  private final GovernanceArtifactCodecRegistry codecs;
  private final String resource;
  private final String allowedPrefix;
  private final boolean activate;
  private final ObjectMapper mapper = new ObjectMapper().findAndRegisterModules();

  public ClasspathGovernanceBootstrapLoader(
      GovernanceControlPlaneService cps,
      GovernanceArtifactCodecRegistry codecs,
      @Value("${spider.governance.bootstrap.classpath-resource:}") String resource,
      @Value("${spider.governance.bootstrap.allowed-prefix:governance/bootstrap/}")
          String allowedPrefix,
      @Value("${spider.governance.bootstrap.activate:false}") boolean activate) {
    this.cps = cps;
    this.codecs = codecs;
    this.resource = resource == null ? "" : resource.trim();
    this.allowedPrefix = allowedPrefix;
    this.activate = activate;
  }

  @Override
  public ActiveGovernanceSnapshot loadAndPublishActivate(
      GovernanceScope scope, String author, String publisher, String activator) {
    if (resource.isBlank()) {
      throw new IllegalStateException("BOOTSTRAP_RESOURCE_REQUIRED");
    }
    if (resource.contains("..")
        || resource.contains(":")
        || resource.startsWith("/")
        || resource.startsWith("\\")
        || !resource.startsWith(allowedPrefix)) {
      throw new IllegalArgumentException("BOOTSTRAP_PATH_REJECTED");
    }
    try (InputStream in = new ClassPathResource(resource).getInputStream()) {
      JsonNode root = mapper.readTree(in);
      List<br.com.banco.spider.governance.GovernanceArtifactRef> refs = new ArrayList<>();
      for (JsonNode art : root.path("artifacts")) {
        GovernanceArtifactType type = GovernanceArtifactType.valueOf(art.path("type").asText());
        String code = art.path("code").asText();
        String version = art.path("version").asText();
        String schema = art.path("schemaVersion").asText("1.0");
        Object domain =
            switch (type) {
              case ROUTE_DEFINITION ->
                  mapper.treeToValue(art.get("content"), RouteDefinition.class);
              case ADAPTER_BINDING_DESCRIPTOR,
                  CALLBACK_BINDING_DESCRIPTOR,
                  STATUS_QUERY_BINDING_DESCRIPTOR ->
                  mapper.treeToValue(art.get("content"), BindingDescriptor.class);
              default -> throw new IllegalArgumentException("BOOTSTRAP_TYPE_UNSUPPORTED");
            };
        if (domain instanceof BindingDescriptor b && b.adapterKind() != AdapterKind.MOCK) {
          throw new IllegalArgumentException("BOOTSTRAP_NON_MOCK");
        }
        String content = codecs.canonicalize(type, domain);
        GovernanceArtifact registered =
            cps.registerTyped(author, type, code, version, schema, content);
        cps.validateArtifact(author, registered.artifactId());
        cps.publishArtifact(publisher, registered.artifactId());
        refs.add(registered.artifactRef());
      }
      String bundleCode = root.path("bundleCode").asText("bundle:bootstrap");
      String bundleVersion = root.path("bundleVersion").asText("1.0.0");
      GovernanceBundle bundle =
          cps.createBundle(author, bundleCode, bundleVersion, scope, refs);
      cps.validateBundle(author, bundle.bundleId());
      ActiveGovernanceSnapshot snapshot = cps.publishBundle(publisher, bundle.bundleId());
      if (activate) {
        cps.activateSnapshot(activator, scope, snapshot.snapshotId(), "BOOTSTRAP_ACTIVATE");
        log.info("event=bootstrap_activated snapshotId={}", snapshot.snapshotId());
      } else {
        log.info("event=bootstrap_published snapshotId={} activate=false", snapshot.snapshotId());
      }
      return snapshot;
    } catch (IllegalArgumentException | IllegalStateException ex) {
      log.info("event=bootstrap_failed reasonCode={}", ex.getMessage());
      throw ex;
    } catch (Exception ex) {
      log.info("event=bootstrap_failed reasonCode=IO");
      throw new IllegalStateException("BOOTSTRAP_FAILED", ex);
    }
  }
}
