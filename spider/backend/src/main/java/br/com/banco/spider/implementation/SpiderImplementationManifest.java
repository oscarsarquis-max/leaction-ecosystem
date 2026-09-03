package br.com.banco.spider.implementation;

import java.util.List;

public record SpiderImplementationManifest(
    String manifestVersion,
    String productVersion,
    String lastVerifiedAt,
    Baseline baseline,
    String currentPrompt,
    String currentGroup,
    ContextIntelligence contextIntelligence,
    List<ImplementationCapability> capabilities,
    List<ExternalBoundary> externalBoundaries) {

  public record Baseline(
      int backendTests, int frontendTests, int failures, int errors, int skipped) {}

  public record ContextIntelligence(
      String status,
      boolean aiEnabled,
      String aiContextInterpretation,
      String aiProvider,
      String executionPlanning,
      String businessCapabilityComposition,
      String workingCapitalPlan,
      String promptRef,
      List<String> featureFlags,
      List<String> architectureRefs,
      List<String> evidenceRefs,
      String testSummary,
      List<String> limitations) {}

  public record ExternalBoundary(String boundaryCode, String description, boolean active) {}
}
