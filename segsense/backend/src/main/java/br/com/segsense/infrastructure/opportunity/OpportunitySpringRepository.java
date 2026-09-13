package br.com.segsense.infrastructure.opportunity;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

interface OpportunitySpringRepository extends JpaRepository<OpportunityJpaEntity, UUID> {

  boolean existsByEnvironmentIdAndKey(UUID environmentId, String key);

  Optional<OpportunityJpaEntity> findByIdAndPublisherIdAndChannelIdAndEnvironmentId(
      UUID id, UUID publisherId, UUID channelId, UUID environmentId);

  @Query(
      """
      SELECT o FROM OpportunityJpaEntity o
      WHERE o.publisherId = :publisherId
        AND o.channelId = :channelId
        AND o.environmentId = :environmentId
        AND (
          :hasCursor = false
          OR (o.createdAt > :createdAt)
          OR (o.createdAt = :createdAt AND o.id > :id)
        )
      ORDER BY o.createdAt ASC, o.id ASC
      """)
  List<OpportunityJpaEntity> listAfter(
      @Param("publisherId") UUID publisherId,
      @Param("channelId") UUID channelId,
      @Param("environmentId") UUID environmentId,
      @Param("hasCursor") boolean hasCursor,
      @Param("createdAt") Instant createdAt,
      @Param("id") UUID id,
      Pageable pageable);
}
