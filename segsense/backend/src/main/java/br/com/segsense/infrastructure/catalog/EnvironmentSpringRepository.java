package br.com.segsense.infrastructure.catalog;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

interface EnvironmentSpringRepository extends JpaRepository<EnvironmentJpaEntity, UUID> {

  boolean existsByChannelIdAndKey(UUID channelId, String key);

  Optional<EnvironmentJpaEntity> findByIdAndPublisherIdAndChannelId(
      UUID id, UUID publisherId, UUID channelId);

  @Query(
      """
      SELECT e FROM EnvironmentJpaEntity e
      WHERE e.publisherId = :publisherId
        AND e.channelId = :channelId
        AND (
          :hasCursor = false
          OR (e.createdAt > :createdAt)
          OR (e.createdAt = :createdAt AND e.id > :id)
        )
      ORDER BY e.createdAt ASC, e.id ASC
      """)
  List<EnvironmentJpaEntity> listAfter(
      @Param("publisherId") UUID publisherId,
      @Param("channelId") UUID channelId,
      @Param("hasCursor") boolean hasCursor,
      @Param("createdAt") Instant createdAt,
      @Param("id") UUID id,
      Pageable pageable);
}
