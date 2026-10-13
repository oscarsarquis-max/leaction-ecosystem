package br.com.banco.spider.operational.monitor;

import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventType;

public final class MonitorProjectionStates {

  public static final String TECH_RECEIVED = "RECEIVED";
  public static final String TECH_PROCESSING = "PROCESSING";
  public static final String TECH_COMPLETED = "COMPLETED";
  public static final String TECH_UNAVAILABLE = "UNAVAILABLE";
  public static final String TECH_UNKNOWN_EFFECT = "UNKNOWN_EFFECT";
  public static final String TECH_FAILURE = "TECHNICAL_FAILURE";

  public static final String FIN_PENDING = "PENDING";
  public static final String FIN_PAID = "PAID";
  public static final String FIN_REFUSED = "REFUSED";
  public static final String FIN_CANCELLED = "CANCELLED";
  public static final String FIN_UNKNOWN = "UNKNOWN";
  public static final String FIN_NA = "NOT_APPLICABLE";

  public static final String COM_PENDING = "PENDING";
  public static final String COM_ACTIVE = "ACTIVE";
  public static final String COM_RENEWAL_OFF = "RENEWAL_DEACTIVATED";
  public static final String COM_CANCELLED = "CANCELLED";
  public static final String COM_EXPIRED = "EXPIRED";
  public static final String COM_NONE = "NO_SUBSCRIPTION";

  public static final String CREDIT_AVAILABLE = "AVAILABLE";
  public static final String CREDIT_RESERVED = "RESERVED";
  public static final String CREDIT_CONSUMED = "CONSUMED";
  public static final String CREDIT_RELEASED = "RELEASED";
  public static final String CREDIT_EXPIRED = "EXPIRED";
  public static final String CREDIT_NONE = "NO_ENTITLEMENT";

  private MonitorProjectionStates() {}

  public static String technical(String reason, OperationalEventType type, OperationalEventOutcome outcome) {
    if (isSatelliteIdentity(reason)) {
      reason = null;
    }
    String incoming = reason == null ? "" : reason.trim().toUpperCase();
    if (incoming.equals("READY") || incoming.equals("COMPLETED") || incoming.equals("SUCCEEDED")) {
      return TECH_COMPLETED;
    }
    if (incoming.equals("PROVIDER_UNAVAILABLE") || incoming.equals("UNAVAILABLE")) {
      return TECH_UNAVAILABLE;
    }
    if (incoming.equals("UNKNOWN") || incoming.contains("UNKNOWN_EFFECT")) {
      return TECH_UNKNOWN_EFFECT;
    }
    if (incoming.equals("FAILED") || incoming.equals("FAILURE") || incoming.equals("TECHNICAL_FAILURE")) {
      return TECH_FAILURE;
    }
    if (incoming.equals("DISPATCHED") || incoming.equals("PROCESSING") || incoming.contains("STARTED")) {
      return TECH_PROCESSING;
    }
    if (incoming.equals("RECEIVED") || incoming.equals("AUTHENTICATED") || incoming.contains("AUTHORIZED")
        || incoming.contains("VALIDATED")) {
      return TECH_RECEIVED;
    }
    if (type == OperationalEventType.SATELLITE_RESPONSE_RETURNED && outcome == OperationalEventOutcome.SUCCESS) {
      return TECH_COMPLETED;
    }
    if (type == OperationalEventType.SATELLITE_RESPONSE_RETURNED && outcome == OperationalEventOutcome.FAILURE) {
      return TECH_FAILURE;
    }
    if (type == OperationalEventType.CAPABILITY_DISPATCHED
        || type == OperationalEventType.OUTBOUND_REQUEST_STARTED) {
      return TECH_PROCESSING;
    }
    if (type == OperationalEventType.SATELLITE_REQUEST_RECEIVED) {
      return TECH_RECEIVED;
    }
    return incoming.isBlank() ? TECH_RECEIVED : incoming;
  }

  public static String financial(String raw) {
    if (raw == null || raw.isBlank()) {
      return FIN_UNKNOWN;
    }
    String value = raw.trim().toUpperCase();
    if (value.contains("PAID") || value.contains("SETTLED") || value.contains("CONFIRMED")
        || value.equals("COMPLETED")) {
      return FIN_PAID;
    }
    if (value.contains("CANCEL")) {
      return FIN_CANCELLED;
    }
    if (value.contains("FAIL") || value.contains("REFUS") || value.contains("REJECT")
        || value.contains("DENIED")) {
      return FIN_REFUSED;
    }
    if (value.contains("PEND") || value.contains("AUTHORIZED") || value.contains("APPROVED")
        || value.contains("WAITING")) {
      return FIN_PENDING;
    }
    if (value.equals("NOT_APPLICABLE") || value.equals("N/A")) {
      return FIN_NA;
    }
    return FIN_UNKNOWN;
  }

  public static String commercial(String raw) {
    if (raw == null || raw.isBlank()) {
      return null;
    }
    String value = raw.trim().toUpperCase();
    if (value.equals("PACK_ONLY") || value.contains("PACK")) {
      return null;
    }
    if (value.contains("RENEWAL") && (value.contains("OFF") || value.contains("DEACTIV"))) {
      return COM_RENEWAL_OFF;
    }
    if (value.contains("CANCEL")) {
      return COM_CANCELLED;
    }
    if (value.contains("EXPIR")) {
      return COM_EXPIRED;
    }
    if (value.contains("ACTIVE") || value.contains("VIGENT") || value.contains("CURRENT")) {
      return COM_ACTIVE;
    }
    if (value.contains("PEND")) {
      return COM_PENDING;
    }
    if (value.contains("NONE") || value.contains("NO_SUB")) {
      return COM_NONE;
    }
    return raw.trim();
  }

  public static String credit(String raw) {
    if (raw == null || raw.isBlank()) {
      return null;
    }
    String value = raw.trim().toUpperCase();
    if (value.equals("PACK_ONLY")) {
      return CREDIT_NONE;
    }
    if (value.contains("RESERV")) {
      return CREDIT_RESERVED;
    }
    if (value.contains("CONFIRM") || value.contains("CONSUM")) {
      return CREDIT_CONSUMED;
    }
    if (value.contains("RELEASE") || value.contains("LIBER")) {
      return CREDIT_RELEASED;
    }
    if (value.contains("EXPIR")) {
      return CREDIT_EXPIRED;
    }
    if (value.contains("AVAIL")) {
      return CREDIT_AVAILABLE;
    }
    if (value.contains("NONE") || value.contains("NO_ENTITLEMENT")) {
      return CREDIT_NONE;
    }
    return null;
  }

  public static boolean regressesTechnical(String current, String incoming) {
    return technicalRank(incoming) < technicalRank(current);
  }

  public static boolean regressesFinancial(String current, String incoming) {
    return financialRank(incoming) < financialRank(current);
  }

  public static int technicalRank(String state) {
    String value = state == null ? "" : state.toUpperCase();
    if (value.equals(TECH_COMPLETED) || value.equals(TECH_FAILURE) || value.equals(TECH_UNAVAILABLE)
        || value.equals(TECH_UNKNOWN_EFFECT)) {
      return 40;
    }
    if (value.equals(TECH_PROCESSING)) {
      return 30;
    }
    return 10;
  }

  public static int financialRank(String state) {
    String value = state == null ? "" : state.toUpperCase();
    if (value.equals(FIN_PAID) || value.equals(FIN_REFUSED) || value.equals(FIN_CANCELLED)) {
      return 40;
    }
    if (value.equals(FIN_PENDING)) {
      return 20;
    }
    return 10;
  }

  private static boolean isSatelliteIdentity(String reason) {
    return "actionfinance".equals(reason)
        || "segsense".equals(reason)
        || "spiderbank".equals(reason)
        || "lojadepaes".equals(reason);
  }
}
