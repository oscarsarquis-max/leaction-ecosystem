package br.com.banco.spider.governance;

import com.fasterxml.jackson.annotation.JsonAutoDetect;
import com.fasterxml.jackson.annotation.PropertyAccessor;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import java.util.Objects;
import org.springframework.stereotype.Component;

/**
 * Codec versionado do snapshot. V1 byte/digest-compatible quando sem DP profiles; V2 quando há
 * Data Protection Profiles no snapshot.
 */
@Component
public class GovernanceSnapshotCodec {

  public static final String SCHEMA_V1 = "GOVERNANCE_SNAPSHOT_V1";
  public static final String SCHEMA_V2 = "GOVERNANCE_SNAPSHOT_V2";
  /** Alias legado. */
  public static final String SCHEMA = SCHEMA_V1;

  private static final int MAX_BYTES = 2_000_000;

  private final ObjectMapper mapper;
  private final GovernanceArtifactDigestService digests;

  public GovernanceSnapshotCodec(GovernanceArtifactDigestService digests) {
    this.digests = digests;
    this.mapper =
        new ObjectMapper()
            .registerModule(new JavaTimeModule())
            .setVisibility(PropertyAccessor.ALL, JsonAutoDetect.Visibility.NONE)
            .setVisibility(PropertyAccessor.FIELD, JsonAutoDetect.Visibility.ANY)
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)
            .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true)
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
  }

  public String encode(ActiveGovernanceSnapshot snapshot) {
    Objects.requireNonNull(snapshot, "snapshot");
    try {
      String schema =
          snapshot.hasDataProtectionProfiles() ? SCHEMA_V2 : SCHEMA_V1;
      SnapshotEnvelope env =
          new SnapshotEnvelope(
              schema,
              snapshot.snapshotId(),
              snapshot.bundleRef(),
              snapshot.bundleDigest(),
              snapshot.governanceScope().code(),
              snapshot.compiledAt().toString(),
              snapshot.snapshotDigest(),
              mapper.writeValueAsString(snapshot));
      String json = mapper.writeValueAsString(env);
      if (json.length() > MAX_BYTES) {
        throw new IllegalArgumentException("SNAPSHOT_TOO_LARGE");
      }
      return json;
    } catch (IllegalArgumentException ex) {
      throw ex;
    } catch (Exception ex) {
      throw new IllegalArgumentException("SNAPSHOT_ENCODE_FAILED:" + ex.getMessage(), ex);
    }
  }

  public ActiveGovernanceSnapshot decode(String json) {
    Objects.requireNonNull(json, "json");
    if (json.length() > MAX_BYTES) {
      throw new IllegalArgumentException("SNAPSHOT_TOO_LARGE");
    }
    try {
      SnapshotEnvelope env = mapper.readValue(json, SnapshotEnvelope.class);
      if (!SCHEMA_V1.equals(env.schemaVersion()) && !SCHEMA_V2.equals(env.schemaVersion())) {
        throw new IllegalArgumentException("UNKNOWN_SNAPSHOT_SCHEMA");
      }
      ActiveGovernanceSnapshot snap =
          mapper.readValue(env.payloadJson(), ActiveGovernanceSnapshot.class);
      if (SCHEMA_V1.equals(env.schemaVersion()) && snap.hasDataProtectionProfiles()) {
        throw new IllegalStateException("SNAPSHOT_V1_MUST_NOT_CONTAIN_DP");
      }
      if (SCHEMA_V2.equals(env.schemaVersion()) && !snap.hasDataProtectionProfiles()) {
        // V2 exige pelo menos o catálogo DP (pode ser vazio só se schema inconsistente)
        // Permitimos V2 com catálogo DP presente (mesmo que maps vazios de signals).
      }
      String expected =
          digests.digestSnapshot(snap.bundleRef(), snap.bundleDigest(), snap.digestCounts());
      if (!digests.secureEquals(expected, snap.snapshotDigest())) {
        throw new IllegalStateException("SNAPSHOT_DIGEST_MISMATCH");
      }
      return snap;
    } catch (IllegalArgumentException | IllegalStateException ex) {
      throw ex;
    } catch (Exception ex) {
      throw new IllegalArgumentException("SNAPSHOT_DECODE_FAILED:" + ex.getMessage(), ex);
    }
  }

  public record SnapshotEnvelope(
      String schemaVersion,
      String snapshotId,
      String bundleRef,
      String bundleDigest,
      String governanceScope,
      String compiledAt,
      String snapshotDigest,
      String payloadJson) {}
}
