package br.com.segsense.application.catalog;

import java.util.List;

public record CatalogPage<T>(List<T> items, String next, int size) {

  public CatalogPage {
    items = List.copyOf(items);
  }
}
