package br.com.segsense.application.demo;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/** Canonical request fingerprint. Hashes declared text; does not store the raw narrative. */
public final class DemoJourneyRequestFingerprint {

  public static final String FLOW_PUBLIC = "PUBLIC";
  public static final String FLOW_LEGACY = "LEGACY_LABELED";

  private DemoJourneyRequestFingerprint() {}

  public static String of(
      String flow,
      String objective,
      boolean intentionConfirmed,
      String contextChoice,
      String normalizedUrl,
      String sourceId,
      String sourceVersion,
      String declaredTheme,
      String declaredText) {
    return of(
        flow,
        objective,
        intentionConfirmed,
        contextChoice,
        normalizedUrl,
        sourceId,
        sourceVersion,
        declaredTheme,
        declaredText,
        "SATELLITE_GOVERNED",
        "");
  }

  public static String of(
      String flow,
      String objective,
      boolean intentionConfirmed,
      String contextChoice,
      String normalizedUrl,
      String sourceId,
      String sourceVersion,
      String declaredTheme,
      String declaredText,
      String primarySourceType,
      String contributionRoles) {
    return of(
        flow,
        objective,
        intentionConfirmed,
        contextChoice,
        normalizedUrl,
        sourceId,
        sourceVersion,
        declaredTheme,
        declaredText,
        primarySourceType,
        contributionRoles,
        "",
        "",
        "");
  }

  public static String of(
      String flow,
      String objective,
      boolean intentionConfirmed,
      String contextChoice,
      String normalizedUrl,
      String sourceId,
      String sourceVersion,
      String declaredTheme,
      String declaredText,
      String primarySourceType,
      String contributionRoles,
      String dwellingType,
      String insuredAmountCents,
      String coverPeriodMonths) {
    String declaredHash =
        declaredText == null || declaredContextBlank(declaredText) ? "" : sha256(declaredText.trim());
    String canonical =
        String.join(
            "\n",
            "v3",
            "flow=" + empty(flow),
            "objective=" + empty(objective),
            "intentionConfirmed=" + intentionConfirmed,
            "contextChoice=" + empty(contextChoice),
            "normalizedUrl=" + empty(normalizedUrl),
            "sourceId=" + empty(sourceId),
            "sourceVersion=" + empty(sourceVersion),
            "declaredTheme=" + empty(declaredTheme),
            "declaredTextSha256=" + declaredHash,
            "classification=INTERNAL",
            "primarySourceType=" + empty(primarySourceType),
            "contributionRoles=" + empty(contributionRoles),
            "dwellingType=" + empty(dwellingType),
            "insuredAmountCents=" + empty(insuredAmountCents),
            "coverPeriodMonths=" + empty(coverPeriodMonths));
    return sha256(canonical);
  }

  public static String sha256(String value) {
    try {
      return HexFormat.of()
          .formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException e) {
      throw new IllegalStateException(e);
    }
  }

  private static boolean declaredContextBlank(String value) {
    return value == null || value.isBlank();
  }

  private static String empty(String value) {
    return value == null ? "" : value;
  }
}
