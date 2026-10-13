package br.com.banco.spider.operational.monitor;

import java.time.Instant;

public final class MonitorJourneyMerge {

  private MonitorJourneyMerge() {}

  public static MonitorJourneyStage apply(MonitorJourneyStage current, MonitorJourneyStage incoming) {
    if (current == null) {
      return incoming;
    }
    if (incoming == null) {
      return current;
    }
    Instant started = earlier(current.occurredAt(), incoming.occurredAt());
    Instant ended = later(current.completedAt(), incoming.completedAt());
    if (isTerminal(incoming.state()) && ended == null) {
      ended = incoming.occurredAt();
    }
    return incoming.toBuilder()
        .occurredAt(started)
        .completedAt(ended)
        .sortOrder(current.sortOrder())
        .title(enrichTitle(current, incoming))
        .state(preferAdvanced(current.state(), incoming.state()))
        .component(firstNonBlank(incoming.component(), current.component()))
        .executor(firstNonBlank(incoming.executor(), current.executor()))
        .decision(firstNonBlank(incoming.decision(), current.decision()))
        .eventType(firstNonBlank(incoming.eventType(), current.eventType()))
        .definitionKey(firstNonBlank(current.definitionKey(), incoming.definitionKey()))
        .evidenceJson(MonitorJourneyEvidence.append(current.evidenceJson(), firstEvidence(incoming)))
        .attempt(incoming.attempt() == null ? current.attempt() : incoming.attempt())
        .projectionVersion(MonitorJourneyStage.JOURNEY_PROJECTION_VERSION)
        .build();
  }

  private static String enrichTitle(MonitorJourneyStage current, MonitorJourneyStage incoming) {
    if (current.stageId() != null && current.stageId().startsWith("page_")
        && incoming.title() != null && incoming.title().contains("recebida")) {
      String page = current.stageId().substring("page_".length());
      return "Página " + page + " solicitada/recebida";
    }
    return firstNonBlank(incoming.title(), current.title());
  }

  private static boolean isTerminal(String state) {
    return "completed".equals(state) || "failed".equals(state) || "rejected".equals(state);
  }

  private static String preferAdvanced(String current, String incoming) {
    return rank(incoming) >= rank(current) ? incoming : current;
  }

  private static int rank(String state) {
    String value = state == null ? "" : state.toLowerCase();
    if (value.equals("failed") || value.equals("rejected")) {
      return 40;
    }
    if (value.equals("completed")) {
      return 30;
    }
    if (value.equals("running") || value.equals("waiting")) {
      return 20;
    }
    return 10;
  }

  private static Instant earlier(Instant left, Instant right) {
    if (left == null) {
      return right;
    }
    if (right == null) {
      return left;
    }
    return right.isBefore(left) ? right : left;
  }

  private static Instant later(Instant left, Instant right) {
    if (left == null) {
      return right;
    }
    if (right == null) {
      return left;
    }
    return right.isAfter(left) ? right : left;
  }

  private static String firstNonBlank(String preferred, String fallback) {
    return preferred == null || preferred.isBlank() ? fallback : preferred;
  }

  private static java.util.Map<String, String> firstEvidence(MonitorJourneyStage incoming) {
    java.util.List<java.util.Map<String, String>> parsed = MonitorJourneyEvidence.parse(incoming.evidenceJson());
    return parsed.isEmpty() ? java.util.Map.of() : parsed.getFirst();
  }
}
