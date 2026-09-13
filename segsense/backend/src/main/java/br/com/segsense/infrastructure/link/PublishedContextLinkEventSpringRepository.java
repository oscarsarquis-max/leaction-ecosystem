package br.com.segsense.infrastructure.link;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

interface PublishedContextLinkEventSpringRepository
    extends JpaRepository<PublishedContextLinkEventJpaEntity, UUID> {

  @Query(
      """
      SELECT e FROM PublishedContextLinkEventJpaEntity e
      WHERE e.linkId = :linkId
        AND (
          :hasCursor = false
          OR (e.occurredAt > :occurredAt)
          OR (e.occurredAt = :occurredAt AND e.id > :id)
        )
      ORDER BY e.occurredAt ASC, e.id ASC
      """)
  List<PublishedContextLinkEventJpaEntity> listAfter(
      @Param("linkId") UUID linkId,
      @Param("hasCursor") boolean hasCursor,
      @Param("occurredAt") Instant occurredAt,
      @Param("id") UUID id,
      Pageable pageable);
}
