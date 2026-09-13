package br.com.segsense.inbound.http.catalog;

import java.util.List;

public record CatalogCollectionResponse<T>(List<T> items, CatalogPageResponse page) {}
