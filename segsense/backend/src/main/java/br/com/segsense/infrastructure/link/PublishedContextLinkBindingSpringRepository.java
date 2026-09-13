package br.com.segsense.infrastructure.link;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface PublishedContextLinkBindingSpringRepository
    extends JpaRepository<PublishedContextLinkBindingJpaEntity, UUID> {

  List<PublishedContextLinkBindingJpaEntity> findByLinkIdOrderByFieldKeyAsc(UUID linkId);
}
