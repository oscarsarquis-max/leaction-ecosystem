package br.com.banco.spider.operational.health;

public record SliDefinition(
    int schemaVersion,
    String code,
    int version,
    String title,
    String functionalDescription,
    HealthDimensionCode dimension,
    String unit,
    int minimumSampleSize,
    boolean higherIsBetter,
    boolean reliabilityStyle) {}
