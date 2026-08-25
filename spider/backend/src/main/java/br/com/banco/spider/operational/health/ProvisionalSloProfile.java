package br.com.banco.spider.operational.health;

import java.util.List;

public record ProvisionalSloProfile(
    int schemaVersion,
    String profileCode,
    String integrationLevel,
    boolean provisional,
    List<ProvisionalSloObjective> objectives) {
  public ProvisionalSloProfile {
    objectives = objectives == null ? List.of() : List.copyOf(objectives);
  }
}
