package br.com.segsense.domain.catalog;

public enum LifecycleStatus {
  DRAFT,
  ACTIVE,
  SUSPENDED;

  public boolean canTransitionTo(LifecycleStatus target) {
    if (target == null || target == DRAFT) {
      return false;
    }
    return switch (this) {
      case DRAFT -> target == ACTIVE;
      case ACTIVE -> target == SUSPENDED;
      case SUSPENDED -> target == ACTIVE;
    };
  }
}
