package br.com.banco.spider.governance;

import static org.assertj.core.api.Assertions.assertThat;

import br.com.banco.spider.execution.signal.ExternalSignalDefinition;
import br.com.banco.spider.governance.catalog.SnapshotBackedDataProtectionProfileCatalog;
import br.com.banco.spider.security.dataprotection.DataProtectionProfileDefinition;
import java.time.Instant;
import java.util.Map;
import org.junit.jupiter.api.Test;

/** Prove que Signal Definition referencia DP profile do snapshot histórico — sem fallback. */
class DataProtectionGovernedCatalogTest {

  @Test
  void snapshotBackedCatalogResolvesPublishedOnly() {
    DataProtectionProfileDefinition published =
        DataProtectionProfileDefinition.publishedAes256(
            "signal-envelope", "1.0", "key:dp:signal-envelope@v1", "v1");
    ActiveGovernanceSnapshot snap =
        new ActiveGovernanceSnapshot(
            "snap-1",
            "b@1",
            "d1",
            new GovernanceScope("DEFAULT"),
            Instant.now(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(
                "signal:async@1.0",
                ExternalSignalDefinition.publishedMock(
                    "async", "1.0", "contract:async", "integrity:sig@1.0", published.exactRef())),
            Map.of(published.exactRef(), published),
            "digest");

    SnapshotBackedDataProtectionProfileCatalog catalog =
        new SnapshotBackedDataProtectionProfileCatalog(snap);
    assertThat(catalog.findPublished(published.exactRef())).isPresent();
    assertThat(catalog.findPublished("dp:missing@9.9")).isEmpty();

    ExternalSignalDefinition signal = snap.externalSignal("signal:async@1.0").orElseThrow();
    assertThat(signal.dataProtectionProfileRef()).isEqualTo(published.exactRef());
    assertThat(GovernanceArtifactType.DATA_PROTECTION_PROFILE.name())
        .isEqualTo("DATA_PROTECTION_PROFILE");
  }
}
