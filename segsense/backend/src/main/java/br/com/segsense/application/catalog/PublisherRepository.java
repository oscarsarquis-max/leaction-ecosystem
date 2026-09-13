package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.Publisher;
import br.com.segsense.domain.catalog.ResourceKey;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface PublisherRepository {

  Publisher save(Publisher publisher);

  Optional<Publisher> findById(UUID id);

  boolean existsByKey(ResourceKey key);

  List<Publisher> listAfter(CatalogCursor after, int limit);
}
