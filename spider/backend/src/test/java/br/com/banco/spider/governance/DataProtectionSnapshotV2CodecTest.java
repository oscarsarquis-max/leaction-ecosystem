package br.com.banco.spider.governance;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import br.com.banco.spider.security.dataprotection.DataProtectionProfileDefinition;
import java.time.Instant;
import java.util.Map;
import org.junit.jupiter.api.Test;

class DataProtectionSnapshotV2CodecTest {

  @Test
  void v1WithoutDpRemainsCompatibleAndV2WhenDpPresent() {
    GovernanceArtifactDigestService digests = new GovernanceArtifactDigestService();
    GovernanceSnapshotCodec codec = new GovernanceSnapshotCodec(digests);

    ActiveGovernanceSnapshot v1 =
        new ActiveGovernanceSnapshot(
            "snap-v1",
            "bundle@1.0",
            "bd1",
            new GovernanceScope("DEFAULT"),
            Instant.parse("2026-01-01T00:00:00Z"),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            digests.digestSnapshot(
                "bundle@1.0",
                "bd1",
                "routes=0;retries=0;waits=0;callbacks=0;bindings=0"));

    String jsonV1 = codec.encode(v1);
    assertThat(jsonV1).contains("GOVERNANCE_SNAPSHOT_V1");
    assertThat(jsonV1).doesNotContain("GOVERNANCE_SNAPSHOT_V2");
    ActiveGovernanceSnapshot decodedV1 = codec.decode(jsonV1);
    assertThat(decodedV1.dataProtectionProfiles()).isEmpty();
    assertThat(decodedV1.snapshotDigest()).isEqualTo(v1.snapshotDigest());

    DataProtectionProfileDefinition dp =
        DataProtectionProfileDefinition.publishedAes256(
            "signal-envelope", "1.0", "key:dp:signal-envelope@v1", "v1");
    String counts =
        "routes=0;retries=0;waits=0;callbacks=0;bindings=0;dp=1";
    ActiveGovernanceSnapshot v2 =
        new ActiveGovernanceSnapshot(
            "snap-v2",
            "bundle@2.0",
            "bd2",
            new GovernanceScope("DEFAULT"),
            Instant.parse("2026-01-02T00:00:00Z"),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(dp.exactRef(), dp),
            digests.digestSnapshot("bundle@2.0", "bd2", counts));

    String jsonV2 = codec.encode(v2);
    assertThat(jsonV2).contains("GOVERNANCE_SNAPSHOT_V2");
    ActiveGovernanceSnapshot decodedV2 = codec.decode(jsonV2);
    assertThat(decodedV2.dataProtectionProfiles()).containsKey(dp.exactRef());
    assertThat(decodedV2.dataProtectionProfiles().get(dp.exactRef()).keyRef())
        .isEqualTo("key:dp:signal-envelope@v1");
    assertThat(jsonV2).doesNotContain("MOCK-DP");
  }

  @Test
  void unknownSchemaFailsClosed() {
    GovernanceSnapshotCodec codec =
        new GovernanceSnapshotCodec(new GovernanceArtifactDigestService());
    assertThatThrownBy(() -> codec.decode("{\"schemaVersion\":\"GOVERNANCE_SNAPSHOT_V99\"}"))
        .isInstanceOf(IllegalArgumentException.class);
  }
}
