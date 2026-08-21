package br.com.banco.spider.governance;

import java.util.Locale;
import java.util.Objects;
import java.util.regex.Pattern;

public record GovernanceArtifactRef(
    GovernanceArtifactType artifactType, String artifactCode, String artifactVersion) {

  private static final Pattern CODE =
      Pattern.compile("^[a-zA-Z0-9][a-zA-Z0-9:_./-]{0,119}$");
  private static final Pattern VERSION = Pattern.compile("^[a-zA-Z0-9][a-zA-Z0-9._-]{0,39}$");

  public GovernanceArtifactRef {
    Objects.requireNonNull(artifactType, "artifactType");
    Objects.requireNonNull(artifactCode, "artifactCode");
    Objects.requireNonNull(artifactVersion, "artifactVersion");
    artifactCode = artifactCode.trim();
    artifactVersion = artifactVersion.trim();
    if (!CODE.matcher(artifactCode).matches()) {
      throw new IllegalArgumentException("invalid artifactCode");
    }
    if (!VERSION.matcher(artifactVersion).matches()) {
      throw new IllegalArgumentException("invalid artifactVersion");
    }
    String lower = artifactVersion.toLowerCase(Locale.ROOT);
    if (lower.equals("latest") || lower.contains("*") || lower.contains(",") || lower.contains("[")) {
      throw new IllegalArgumentException("floating versions not allowed");
    }
  }

  public String exactRef() {
    return artifactCode + "@" + artifactVersion;
  }

  @Override
  public String toString() {
    return artifactType + ":" + exactRef();
  }
}
