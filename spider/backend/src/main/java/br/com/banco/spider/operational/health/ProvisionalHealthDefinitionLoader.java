package br.com.banco.spider.operational.health;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.InputStream;
import java.util.List;
import org.springframework.core.io.ClassPathResource;

public class ProvisionalHealthDefinitionLoader {

  public static final String SLI_PATH = "implementation/sli-definitions-v1.json";
  public static final String SLO_PATH = "implementation/provisional-slo-profile-v1.json";
  private final List<SliDefinition> definitions;
  private final ProvisionalSloProfile profile;

  public ProvisionalHealthDefinitionLoader(ObjectMapper mapper) {
    try (InputStream definitionsInput = new ClassPathResource(SLI_PATH).getInputStream();
        InputStream profileInput = new ClassPathResource(SLO_PATH).getInputStream()) {
      definitions =
          List.copyOf(
              mapper.readValue(definitionsInput, new TypeReference<List<SliDefinition>>() {}));
      profile = mapper.readValue(profileInput, ProvisionalSloProfile.class);
      if (definitions.size() != 6
          || profile.schemaVersion() != 1
          || !profile.provisional()
          || !"MOCK_ONLY".equals(profile.integrationLevel())) {
        throw new IllegalStateException("Invalid provisional health definitions");
      }
    } catch (Exception failure) {
      throw new IllegalStateException("Could not load provisional health definitions", failure);
    }
  }

  public List<SliDefinition> definitions() {
    return definitions;
  }

  public ProvisionalSloProfile profile() {
    return profile;
  }
}
