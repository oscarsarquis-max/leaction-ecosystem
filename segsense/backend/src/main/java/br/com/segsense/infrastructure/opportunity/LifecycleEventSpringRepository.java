package br.com.segsense.infrastructure.opportunity;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

interface LifecycleEventSpringRepository extends JpaRepository<LifecycleEventJpaEntity, UUID> {

  @Query(
      """
      SELECT e FROM LifecycleEventJpaEntity e
      WHERE e.opportunityId = :opportunityId
        AND (
          :hasCursor = false
          OR (e.occurredAt > :occurredAt)
          OR (e.occurredAt = :occurredAt AND e.id > :id)
        )
      ORDER BY e.occurredAt ASC, e.id ASC
      """)
  List<LifecycleEventJpaEntity> listAfter(
      @Param("opportunityId") UUID opportunityId,
      @Param("hasCursor") boolean hasCursor,
      @Param("occurredAt") Instant occurredAt,
      @Param("id") UUID id,
      Pageable pageable);
}
