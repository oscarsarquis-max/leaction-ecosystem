package br.com.segsense.infrastructure.catalog;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

interface PublisherSpringRepository extends JpaRepository<PublisherJpaEntity, UUID> {

  boolean existsByKey(String key);

  @Query(
      """
      SELECT p FROM PublisherJpaEntity p
      WHERE :hasCursor = false
         OR (p.createdAt > :createdAt)
         OR (p.createdAt = :createdAt AND p.id > :id)
      ORDER BY p.createdAt ASC, p.id ASC
      """)
  List<PublisherJpaEntity> listAfter(
      @Param("hasCursor") boolean hasCursor,
      @Param("createdAt") Instant createdAt,
      @Param("id") UUID id,
      Pageable pageable);
}
