package br.com.banco.spider.governance;

import java.util.Objects;

public record GovernanceScope(String code) {
  public static final GovernanceScope DEFAULT = new GovernanceScope("DEFAULT");

  public GovernanceScope {
    Objects.requireNonNull(code, "code");
    code = code.trim();
    if (code.isEmpty() || code.length() > 64) {
      throw new IllegalArgumentException("invalid scope");
    }
  }
}
