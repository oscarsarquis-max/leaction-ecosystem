package br.com.segsense.infrastructure.link;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

interface PublishedContextLinkSpringRepository
    extends JpaRepository<PublishedContextLinkJpaEntity, UUID> {

  Optional<PublishedContextLinkJpaEntity>
      findByIdAndPublisherIdAndChannelIdAndEnvironmentIdAndOpportunityId(
          UUID id, UUID publisherId, UUID channelId, UUID environmentId, UUID opportunityId);

  Optional<PublishedContextLinkJpaEntity> findByTokenDigest(byte[] tokenDigest);

  @Query(
      """
      SELECT l FROM PublishedContextLinkJpaEntity l
      WHERE l.opportunityId = :opportunityId
        AND (
          :hasCursor = false
          OR (l.issuedAt < :issuedAt)
          OR (l.issuedAt = :issuedAt AND l.id < :id)
        )
      ORDER BY l.issuedAt DESC, l.id DESC
      """)
  List<PublishedContextLinkJpaEntity> listAfter(
      @Param("opportunityId") UUID opportunityId,
      @Param("hasCursor") boolean hasCursor,
      @Param("issuedAt") Instant issuedAt,
      @Param("id") UUID id,
      Pageable pageable);
}
