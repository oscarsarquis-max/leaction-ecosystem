package br.com.banco.spider.context.application;

import java.time.Instant;
import java.util.Map;

/** Fato produzido pelo Context Plane; não representa progresso do Data Plane. */
public record ContextJourneyStage(
    String id,
    String title,
    String layer,
    String state,
    String summary,
    Instant occurredAt,
    Map<String, String> technicalDetails) {

  public ContextJourneyStage {
    technicalDetails = technicalDetails == null ? Map.of() : Map.copyOf(technicalDetails);
  }
}
