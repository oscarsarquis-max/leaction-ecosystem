package br.com.segsense.infrastructure.catalog;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

interface ChannelSpringRepository extends JpaRepository<ChannelJpaEntity, UUID> {

  boolean existsByPublisherIdAndKey(UUID publisherId, String key);

  Optional<ChannelJpaEntity> findByIdAndPublisherId(UUID id, UUID publisherId);

  @Query(
      """
      SELECT c FROM ChannelJpaEntity c
      WHERE c.publisherId = :publisherId
        AND (
          :hasCursor = false
          OR (c.createdAt > :createdAt)
          OR (c.createdAt = :createdAt AND c.id > :id)
        )
      ORDER BY c.createdAt ASC, c.id ASC
      """)
  List<ChannelJpaEntity> listAfter(
      @Param("publisherId") UUID publisherId,
      @Param("hasCursor") boolean hasCursor,
      @Param("createdAt") Instant createdAt,
      @Param("id") UUID id,
      Pageable pageable);
}
