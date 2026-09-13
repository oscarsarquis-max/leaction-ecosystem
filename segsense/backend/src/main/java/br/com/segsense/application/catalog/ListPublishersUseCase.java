package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.Publisher;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ListPublishersUseCase {

  private final PublisherRepository publishers;

  public ListPublishersUseCase(PublisherRepository publishers) {
    this.publishers = publishers;
  }

  @Transactional(readOnly = true)
  public CatalogPage<Publisher> execute(CatalogPageQuery query) {
    CatalogCursor cursor = query.decodedCursor();
    List<Publisher> fetched = publishers.listAfter(cursor, query.size() + 1);
    return CatalogPages.slice(fetched, query.size(), Publisher::createdAt, Publisher::id);
  }
}
