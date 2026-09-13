package br.com.segsense.domain.opportunity;

import java.time.Instant;

public final class PublicationWindow {

  private PublicationWindow() {}

  public static boolean isOpen(OpportunityContent content, Instant now) {
    Instant from = content.validFrom();
    Instant until = content.validUntil();
    if (from != null && now.isBefore(from)) {
      return false;
    }
    if (until != null && !now.isBefore(until)) {
      return false;
    }
    return true;
  }

  public static boolean isExpired(OpportunityContent content, Instant now) {
    Instant until = content.validUntil();
    return until != null && !now.isBefore(until);
  }
}
