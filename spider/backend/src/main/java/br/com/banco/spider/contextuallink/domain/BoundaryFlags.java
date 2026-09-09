package br.com.banco.spider.contextuallink.domain;

public record BoundaryFlags(
    boolean intentCreated,
    boolean executionPlanCreated,
    boolean dataPlaneStarted) {

  public static BoundaryFlags demo001() {
    return new BoundaryFlags(false, false, false);
  }

  public BoundaryFlags afterUnderstand(boolean planCreated) {
    return new BoundaryFlags(true, planCreated, false);
  }
}
