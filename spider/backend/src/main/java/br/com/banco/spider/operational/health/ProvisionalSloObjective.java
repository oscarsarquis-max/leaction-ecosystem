package br.com.banco.spider.operational.health;

public record ProvisionalSloObjective(
    String code,
    String sliCode,
    Double target,
    String threshold,
    boolean higherIsBetter,
    double atRiskFactor) {}
