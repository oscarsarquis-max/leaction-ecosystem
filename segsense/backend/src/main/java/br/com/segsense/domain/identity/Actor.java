package br.com.segsense.domain.identity;

import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Objects;
import java.util.Set;

/**
 * Authenticated actor of the satellite. Never constructed from browser-supplied headers, query
 * strings or user payloads. Distinct from {@link ApplicationIdentity} and {@link ChannelContext}.
 */
public record Actor(String subjectId, ActorType type, Set<String> roles) {

  public Actor {
    subjectId = IdentityValues.requireNormalized(subjectId, "subjectId");
    Objects.requireNonNull(type, "type must not be null");
    roles = normalizeRoles(roles);
  }

  public static Actor of(String subjectId, ActorType type, Set<String> roles) {
    return new Actor(subjectId, type, roles);
  }

  private static Set<String> normalizeRoles(Set<String> raw) {
    if (raw == null || raw.isEmpty()) {
      return Set.of();
    }
    Set<String> normalized = new LinkedHashSet<>();
    for (String role : raw) {
      String value = IdentityValues.requireNormalized(role, "role");
      normalized.add(value);
    }
    return Collections.unmodifiableSet(normalized);
  }
}
