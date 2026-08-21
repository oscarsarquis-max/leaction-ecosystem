package br.com.banco.spider.governance;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Base64;
import java.util.Objects;
import org.springframework.stereotype.Service;

@Service
public class GovernanceArtifactDigestService {

  public static final String ALGORITHM = "SHA-256";

  public String digestArtifact(
      GovernanceArtifactType type,
      String code,
      String version,
      String schemaVersion,
      String canonicalContent) {
    Objects.requireNonNull(type, "type");
    Objects.requireNonNull(code, "code");
    Objects.requireNonNull(version, "version");
    Objects.requireNonNull(schemaVersion, "schemaVersion");
    Objects.requireNonNull(canonicalContent, "canonicalContent");
    String material =
        "SPIDER/GOV/ARTIFACT/V1\n"
            + type.name()
            + "\n"
            + code
            + "\n"
            + version
            + "\n"
            + schemaVersion
            + "\n"
            + canonicalContent;
    return sha256Base64Url(material);
  }

  public String digestBundle(
      String bundleCode, String bundleVersion, GovernanceScope scope, String orderedRefsWithDigests) {
    String material =
        "SPIDER/GOV/BUNDLE/V1\n"
            + scope.code()
            + "\n"
            + bundleCode
            + "\n"
            + bundleVersion
            + "\n"
            + orderedRefsWithDigests;
    return sha256Base64Url(material);
  }

  public String digestSnapshot(String bundleRef, String bundleDigest, String orderedTypeCounts) {
    String material =
        "SPIDER/GOV/SNAPSHOT/V1\n" + bundleRef + "\n" + bundleDigest + "\n" + orderedTypeCounts;
    return sha256Base64Url(material);
  }

  public boolean secureEquals(String a, String b) {
    if (a == null || b == null) {
      return false;
    }
    return MessageDigest.isEqual(
        a.getBytes(StandardCharsets.UTF_8), b.getBytes(StandardCharsets.UTF_8));
  }

  private static String sha256Base64Url(String material) {
    try {
      MessageDigest md = MessageDigest.getInstance("SHA-256");
      byte[] dig = md.digest(material.getBytes(StandardCharsets.UTF_8));
      return Base64.getUrlEncoder().withoutPadding().encodeToString(dig);
    } catch (Exception ex) {
      throw new IllegalStateException("digest failure");
    }
  }
}
