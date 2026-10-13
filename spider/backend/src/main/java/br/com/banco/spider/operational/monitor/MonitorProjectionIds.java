package br.com.banco.spider.operational.monitor;

import br.com.banco.spider.satellite.application.DemoSliceRules;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class MonitorProjectionIds {

  static final Pattern LIST_MESSAGE = Pattern.compile("^list-([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})-(\\d+)$");
  static final Pattern LIST_CORR = Pattern.compile("^afp-([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})-(\\d+)$");
  static final Pattern ROOT_CORR = Pattern.compile("^afr-([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$");

  private MonitorProjectionIds() {}

  public static String interaction(SatelliteInteractionRequest request) {
    if (request == null || request.satelliteId() == null || request.satelliteId().isBlank()) {
      return null;
    }
    String messageId = request.messageId();
    if (blank(messageId)) {
      return null;
    }
    return "int:" + request.satelliteId().trim() + ":" + messageId.trim();
  }

  public static String sync(SatelliteInteractionRequest request) {
    String runId = syncRunId(request);
    String companyId = DemoSliceRules.requestedCompanyId(request);
    String environment = environment(request);
    return sync(companyId, environment, runId);
  }

  public static String sync(String companyId, String environment, String syncRunId) {
    if (blank(companyId) || blank(environment) || blank(syncRunId)) {
      return null;
    }
    return "sync:" + companyId.trim() + ":" + environment.trim() + ":" + syncRunId.trim();
  }

  public static String payment(String companyId, String transactionId) {
    if (blank(companyId) || blank(transactionId)) {
      return null;
    }
    return "pay:" + companyId.trim() + ":" + transactionId.trim();
  }

  public static String eventKey(SatelliteInteractionRequest request) {
    if (isListSync(request)) {
      String syncId = sync(request);
      if (syncId != null) {
        return syncId;
      }
    }
    return interaction(request);
  }

  public static boolean isListSync(SatelliteInteractionRequest request) {
    return request != null
        && "actionfinance".equals(request.satelliteId())
        && SatelliteContractV1.PURPOSE_FINANCIAL_EXTERNAL_LIST.equals(request.purpose())
        && syncRunId(request) != null;
  }

  public static String syncRunId(SatelliteInteractionRequest request) {
    if (request == null) {
      return null;
    }
    Map<String, Object> list = DemoSliceRules.financialList(request);
    String explicit = text(list.get("syncRunId"));
    if (!blank(explicit)) {
      return explicit;
    }
    String fromMessage = capture(LIST_MESSAGE, request.messageId(), 1);
    if (fromMessage != null) {
      return fromMessage;
    }
    String fromPage = capture(LIST_CORR, request.correlationId(), 1);
    if (fromPage != null) {
      return fromPage;
    }
    return capture(ROOT_CORR, request.correlationId(), 1);
  }

  public static Integer pageNumber(SatelliteInteractionRequest request) {
    if (request == null) {
      return null;
    }
    Map<String, Object> list = DemoSliceRules.financialList(request);
    Object raw = list.get("page");
    if (raw instanceof Number number) {
      return number.intValue();
    }
    Integer fromMessage = captureInt(LIST_MESSAGE, request.messageId(), 2);
    if (fromMessage != null) {
      return fromMessage;
    }
    return captureInt(LIST_CORR, request.correlationId(), 2);
  }

  public static String environment(SatelliteInteractionRequest request) {
    String environment = text(DemoSliceRules.financialList(request).get("environment"));
    if (!blank(environment)) {
      return environment;
    }
    environment = text(DemoSliceRules.financialLookup(request).get("environment"));
    return blank(environment) ? null : environment;
  }

  public static String maskExternal(String value) {
    if (value == null || value.length() < 8) {
      return value;
    }
    return value.substring(0, 4) + "…" + value.substring(value.length() - 4);
  }

  private static String capture(Pattern pattern, String value, int group) {
    if (blank(value)) {
      return null;
    }
    Matcher matcher = pattern.matcher(value.trim());
    return matcher.matches() ? matcher.group(group) : null;
  }

  private static Integer captureInt(Pattern pattern, String value, int group) {
    String captured = capture(pattern, value, group);
    if (captured == null) {
      return null;
    }
    try {
      return Integer.parseInt(captured);
    } catch (NumberFormatException ignored) {
      return null;
    }
  }

  private static String text(Object value) {
    return value == null ? "" : String.valueOf(value).trim();
  }

  private static boolean blank(String value) {
    return value == null || value.isBlank();
  }
}
