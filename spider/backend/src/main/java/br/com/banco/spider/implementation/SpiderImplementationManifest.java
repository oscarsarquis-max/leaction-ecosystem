package br.com.banco.spider.implementation;

import java.util.List;

public record SpiderImplementationManifest(
    String manifestVersion,
    String productVersion,
    String lastVerifiedAt,
    Baseline baseline,
    String currentPrompt,
    String currentGroup,
    List<ImplementationCapability> capabilities,
    List<ExternalBoundary> externalBoundaries) {

  public record Baseline(
      int backendTests, int frontendTests, int failures, int errors, int skipped) {}

  public record ExternalBoundary(String boundaryCode, String description, boolean active) {}
}
