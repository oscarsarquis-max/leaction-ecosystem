package br.com.banco.spider.governance;

import java.util.Objects;

public record GovernedWorkItemRef(GovernedWorkItemType type, String workItemId) {

  public GovernedWorkItemRef {
    Objects.requireNonNull(type, "type");
    Objects.requireNonNull(workItemId, "workItemId");
    workItemId = workItemId.trim();
    if (workItemId.isEmpty()) {
      throw new IllegalArgumentException("workItemId blank");
    }
  }
}
