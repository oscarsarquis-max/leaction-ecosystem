package br.com.segsense.infrastructure.opportunity;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

interface OpportunityRevisionSpringRepository
    extends JpaRepository<OpportunityRevisionJpaEntity, UUID> {

  Optional<OpportunityRevisionJpaEntity> findByOpportunityIdAndRevisionNumber(
      UUID opportunityId, int revisionNumber);

  @Query(
      """
      SELECT r FROM OpportunityRevisionJpaEntity r
      WHERE r.opportunityId = :opportunityId
        AND (
          :hasCursor = false
          OR r.revisionNumber > :afterRevision
        )
      ORDER BY r.revisionNumber ASC
      """)
  List<OpportunityRevisionJpaEntity> listAfter(
      @Param("opportunityId") UUID opportunityId,
      @Param("hasCursor") boolean hasCursor,
      @Param("afterRevision") int afterRevision,
      Pageable pageable);
}
