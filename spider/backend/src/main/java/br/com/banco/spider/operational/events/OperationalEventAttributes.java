package br.com.banco.spider.operational.events;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

public final class OperationalEventAttributes {

  private static final int MAX_ENTRIES = 16;
  private static final int MAX_VALUE_LENGTH = 200;
  private static final Set<String> ALLOWED =
      Set.of(
          "reasonCode",
          "stepRef",
          "waitId",
          "routeCode",
          "technicalStatus",
          "httpStatus",
          "disposition",
          "signalOutcome",
          "integrityReason",
          "component",
          "workerType",
          "scheduleCode");

  private final Map<String, String> values;

  private OperationalEventAttributes(Map<String, String> values) {
    this.values = Map.copyOf(values);
  }

  public static Builder builder() {
    return new Builder();
  }

  public static OperationalEventAttributes empty() {
    return new OperationalEventAttributes(Map.of());
  }

  public Map<String, String> toMap() {
    return values;
  }

  public static final class Builder {
    private final Map<String, String> values = new LinkedHashMap<>();

    public Builder reasonCode(String value) {
      return put("reasonCode", value);
    }

    public Builder stepRef(String value) {
      return put("stepRef", value);
    }

    public Builder waitId(String value) {
      return put("waitId", value);
    }

    public Builder routeCode(String value) {
      return put("routeCode", value);
    }

    public Builder technicalStatus(String value) {
      return put("technicalStatus", value);
    }

    public Builder httpStatus(String value) {
      return put("httpStatus", value);
    }

    public Builder disposition(String value) {
      return put("disposition", value);
    }

    public Builder signalOutcome(String value) {
      return put("signalOutcome", value);
    }

    public Builder integrityReason(String value) {
      return put("integrityReason", value);
    }

    public Builder component(String value) {
      return put("component", value);
    }

    public Builder workerType(String value) {
      return put("workerType", value);
    }

    public Builder scheduleCode(String value) {
      return put("scheduleCode", value);
    }

    public Builder put(String key, String value) {
      if (!ALLOWED.contains(key)) {
        return this;
      }
      if (value == null || values.size() >= MAX_ENTRIES && !values.containsKey(key)) {
        return this;
      }
      String normalized = value.length() > MAX_VALUE_LENGTH ? value.substring(0, MAX_VALUE_LENGTH) : value;
      values.put(key, normalized);
      return this;
    }

    public OperationalEventAttributes build() {
      return new OperationalEventAttributes(values);
    }
  }
}
