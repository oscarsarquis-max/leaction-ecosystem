package br.com.segsense.application.catalog;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.function.Function;

public final class CatalogPages {

  private CatalogPages() {}

  public static <T> CatalogPage<T> slice(
      List<T> fetched, int size, Function<T, Instant> createdAt, Function<T, UUID> id) {
    boolean hasNext = fetched.size() > size;
    List<T> items = new ArrayList<>(hasNext ? fetched.subList(0, size) : fetched);
    String next = null;
    if (hasNext && !items.isEmpty()) {
      T last = items.get(items.size() - 1);
      next = CatalogCursor.encode(createdAt.apply(last), id.apply(last));
    }
    return new CatalogPage<>(items, next, size);
  }
}
