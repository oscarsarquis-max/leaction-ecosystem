package br.com.segsense.infrastructure.demonstration;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

interface DemonstrationDecisionSpringRepository
    extends JpaRepository<DemonstrationDecisionJpaEntity, UUID> {

  @Query(
      """
      SELECT MAX(d.decidedAt) FROM DemonstrationDecisionJpaEntity d
      WHERE d.storyId = :storyId AND d.action IN ('PUBLISHED', 'RESUMED')
      """)
  Optional<Instant> lastPublicationAt(@Param("storyId") UUID storyId);
}
