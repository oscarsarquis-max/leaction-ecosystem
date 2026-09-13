package br.com.segsense.application.consent;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

class CredentialCacheAbsenceTest {

  @Test
  void useCaseDoesNotRetainRawCredentialsInMemory() throws Exception {
    String source =
        Files.readString(
            Path.of("src/main/java/br/com/segsense/application/consent/ManageContextInstanceUseCase.java"));
    assertThat(source).doesNotContain("ConcurrentHashMap");
    assertThat(source).doesNotContain("IssuedCredential");
    assertThat(source).doesNotContain("issued.put");
    assertThat(source).doesNotContain("Redis");
  }
}
