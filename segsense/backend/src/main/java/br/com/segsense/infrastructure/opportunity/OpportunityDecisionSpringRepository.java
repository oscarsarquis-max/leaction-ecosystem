package br.com.segsense.infrastructure.opportunity;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface OpportunityDecisionSpringRepository
    extends JpaRepository<OpportunityDecisionJpaEntity, UUID> {

  Optional<OpportunityDecisionJpaEntity> findFirstByOpportunityIdOrderByDecidedAtDesc(
      UUID opportunityId);

  Optional<OpportunityDecisionJpaEntity> findBySubmissionId(UUID submissionId);
}
