package br.com.banco.spider.implementation;

import java.util.List;

public record ImplementationCapability(
    String capabilityCode,
    String groupCode,
    String promptRef,
    String title,
    String objective,
    String status,
    String runtimeAvailability,
    String integrationLevel,
    List<String> architectureRefs,
    List<String> technicalDocRefs,
    List<String> featureFlags,
    List<String> evidenceRefs,
    String testSummary,
    List<String> dependencies,
    List<String> limitations,
    String lastVerifiedAt) {}
