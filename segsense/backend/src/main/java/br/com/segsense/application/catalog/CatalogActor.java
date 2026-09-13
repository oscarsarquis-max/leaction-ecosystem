package br.com.segsense.application.catalog;

public record CatalogActor(String subjectId) {

  public CatalogActor {
    if (subjectId == null || subjectId.isBlank()) {
      throw new IllegalArgumentException("subjectId is required");
    }
    subjectId = subjectId.trim();
  }
}
