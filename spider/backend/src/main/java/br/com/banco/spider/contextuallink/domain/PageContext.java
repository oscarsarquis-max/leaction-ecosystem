package br.com.banco.spider.contextuallink.domain;

import java.time.Instant;
import java.util.Objects;

/**
 * Projeção da página de origem. Conteúdo tratado como dado não confiável. Sem Intent.
 */
public record PageContext(
    String contextId,
    String clickId,
    String sourceUrl,
    String sourceTitle,
    String sourceOrigin,
    String contentFingerprint,
    Instant acquisitionTimestamp,
    ContextAcquisitionStatus acquisitionStatus,
    String safeExtractedText) {

  public PageContext {
    Objects.requireNonNull(contextId, "contextId");
    Objects.requireNonNull(clickId, "clickId");
    Objects.requireNonNull(acquisitionStatus, "acquisitionStatus");
    sourceUrl = sourceUrl == null ? "" : sourceUrl;
    sourceTitle = sourceTitle == null ? "" : sourceTitle;
    sourceOrigin = sourceOrigin == null ? "" : sourceOrigin;
    contentFingerprint = contentFingerprint == null ? "" : contentFingerprint;
    safeExtractedText = safeExtractedText == null ? "" : safeExtractedText;
  }

  public static PageContext unavailable(
      String contextId, String clickId, Instant at, ContextAcquisitionStatus status) {
    return new PageContext(contextId, clickId, "", "", "", "", at, status, "");
  }
}
