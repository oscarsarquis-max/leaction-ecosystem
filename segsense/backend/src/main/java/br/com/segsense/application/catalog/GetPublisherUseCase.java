package br.com.segsense.application.catalog;

import br.com.segsense.domain.catalog.Publisher;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class GetPublisherUseCase {

  private final PublisherRepository publishers;

  public GetPublisherUseCase(PublisherRepository publishers) {
    this.publishers = publishers;
  }

  @Transactional(readOnly = true)
  public Publisher execute(UUID publisherId) {
    return publishers.findById(publisherId).orElseThrow(ResourceNotFoundException::new);
  }
}
