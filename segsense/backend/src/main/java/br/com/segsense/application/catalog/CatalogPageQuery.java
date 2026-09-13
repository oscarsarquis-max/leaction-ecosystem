package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.CatalogValidationException;

public record CatalogPageQuery(int size, String after) {

  public static final int DEFAULT_SIZE = 20;
  public static final int MAX_SIZE = 100;

  public CatalogPageQuery {
    if (size < 1 || size > MAX_SIZE) {
      throw new CatalogValidationException("O tamanho da página deve estar entre 1 e 100.");
    }
  }

  public static CatalogPageQuery of(Integer size, String after) {
    int resolved = size == null ? DEFAULT_SIZE : size;
    return new CatalogPageQuery(resolved, after == null || after.isBlank() ? null : after);
  }

  public CatalogCursor decodedCursor() {
    if (after == null) {
      return null;
    }
    return CatalogCursor.decode(after);
  }
}
