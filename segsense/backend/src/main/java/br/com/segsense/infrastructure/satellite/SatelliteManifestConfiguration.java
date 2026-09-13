package br.com.segsense.infrastructure.satellite;

import br.com.segsense.application.satellite.SatelliteIdentityGuard;
import br.com.segsense.application.satellite.SatelliteManifest;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.ClassPathResource;
import org.yaml.snakeyaml.Yaml;

@Configuration
public class SatelliteManifestConfiguration {

  @Bean
  public SatelliteManifest satelliteManifest(
      @Value("${segsense.satellite.application-id}") String configuredApplicationId)
      throws IOException {
    return load(new ClassPathResource("satellite-manifest.yaml"), configuredApplicationId);
  }

  static SatelliteManifest load(org.springframework.core.io.Resource resource, String configuredApplicationId)
      throws IOException {
    try (InputStream input = resource.getInputStream()) {
      Yaml yaml = new Yaml();
      Object loaded = yaml.load(input);
      if (!(loaded instanceof Map<?, ?> raw)) {
        throw new IllegalStateException("Satellite manifest is not a YAML mapping");
      }
      SatelliteManifest manifest = from(raw);
      SatelliteIdentityGuard.requireMatching(configuredApplicationId, manifest.applicationId());
      return manifest;
    }
  }

  static SatelliteManifest from(Map<?, ?> raw) {
    String classification = requiredString(raw, "classification");
    String schemaVersion = requiredString(raw, "schemaVersion");
    String schemaVersionKind = requiredString(raw, "schemaVersionKind");
    String applicationId = requiredString(raw, "applicationId");
    String domain = requiredString(raw, "domain");
    List<String> allowedOperationClasses = requiredStringList(raw, "allowedOperationClasses");
    String mutationPolicy = requiredString(raw, "mutationPolicy");
    String status = requiredString(raw, "status");
    boolean executable = requiredBoolean(raw, "executable");
    boolean acceptedBySpider = requiredBoolean(raw, "acceptedBySpider");

    if (!"DRAFT / NOT_CERTIFIED".equals(classification)) {
      throw new IllegalStateException("Satellite manifest classification is not DRAFT / NOT_CERTIFIED");
    }
    if (!"PRELIMINARY".equals(schemaVersionKind)) {
      throw new IllegalStateException("Satellite manifest schemaVersionKind is not PRELIMINARY");
    }
    if (!"DRAFT".equals(status)) {
      throw new IllegalStateException("Satellite manifest status is not DRAFT");
    }
    if (executable || acceptedBySpider) {
      throw new IllegalStateException("Satellite manifest must not be executable or accepted by Spider");
    }
    return new SatelliteManifest(
        classification,
        schemaVersion,
        schemaVersionKind,
        applicationId,
        domain,
        List.copyOf(allowedOperationClasses),
        mutationPolicy,
        status,
        executable,
        acceptedBySpider);
  }

  private static String requiredString(Map<?, ?> raw, String key) {
    Object value = raw.get(key);
    if (!(value instanceof String text) || text.isBlank()) {
      throw new IllegalStateException("Satellite manifest field '" + key + "' is missing");
    }
    return text;
  }

  private static boolean requiredBoolean(Map<?, ?> raw, String key) {
    Object value = raw.get(key);
    if (!(value instanceof Boolean flag)) {
      throw new IllegalStateException("Satellite manifest field '" + key + "' is missing");
    }
    return flag;
  }

  private static List<String> requiredStringList(Map<?, ?> raw, String key) {
    Object value = raw.get(key);
    if (!(value instanceof List<?> list) || list.isEmpty()) {
      throw new IllegalStateException("Satellite manifest field '" + key + "' is missing");
    }
    List<String> result = new ArrayList<>();
    for (Object item : list) {
      if (!(item instanceof String text) || text.isBlank()) {
        throw new IllegalStateException("Satellite manifest field '" + key + "' is invalid");
      }
      result.add(text);
    }
    return result;
  }
}
